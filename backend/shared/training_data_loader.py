"""Training data loader for few-shot learning."""
import json
import os
import boto3
from typing import List, Dict, Any, Optional
import base64
from io import BytesIO

# Try to import datasets, but don't fail if not available
try:
    from datasets import load_dataset
    DATASETS_AVAILABLE = True
except ImportError:
    DATASETS_AVAILABLE = False

from config import TRAINING_DATA_BUCKET, FEW_SHOT_EXAMPLE_COUNT, S3_BUCKET_NAME


class TrainingDataLoader:
    """Load and cache training examples for few-shot learning."""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket = TRAINING_DATA_BUCKET or S3_BUCKET_NAME
        self.cache_prefix = 'training-examples/'
        self.local_cache = {}
        
    def get_few_shot_examples(self, count: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get few-shot training examples.
        
        Args:
            count: Number of examples to return (default: FEW_SHOT_EXAMPLE_COUNT)
            
        Returns:
            List of training examples with image data and annotations
        """
        if count is None:
            count = FEW_SHOT_EXAMPLE_COUNT
            
        # Try to load from S3 cache first
        examples = self._load_from_s3_cache(count)
        
        if examples and len(examples) >= count:
            return examples[:count]
        
        # If not enough examples in S3, return empty list
        # (Training data should be prepared using prepare-training-data script)
        return []
    
    def _load_from_s3_cache(self, count: int) -> List[Dict[str, Any]]:
        """Load training examples from S3 cache."""
        examples = []
        
        try:
            # List objects in training-examples/ prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=self.cache_prefix,
                MaxKeys=count * 2  # Get more than needed in case some are invalid
            )
            
            if 'Contents' not in response:
                return []
            
            # Load JSON annotation files
            for obj in response['Contents']:
                key = obj['Key']
                if key.endswith('.json'):
                    try:
                        # Get annotation file
                        annotation_response = self.s3_client.get_object(
                            Bucket=self.bucket,
                            Key=key
                        )
                        annotation = json.loads(annotation_response['Body'].read())
                        
                        # Get corresponding image file
                        image_key = key.replace('.json', '.png')
                        try:
                            image_response = self.s3_client.get_object(
                                Bucket=self.bucket,
                                Key=image_key
                            )
                            image_data = image_response['Body'].read()
                            image_base64 = base64.b64encode(image_data).decode('utf-8')
                            
                            examples.append({
                                'image_base64': image_base64,
                                'image_format': 'png',
                                'annotation': annotation
                            })
                            
                            if len(examples) >= count:
                                break
                                
                        except Exception as e:
                            print(f"Failed to load image {image_key}: {e}")
                            continue
                            
                    except Exception as e:
                        print(f"Failed to load annotation {key}: {e}")
                        continue
                        
        except Exception as e:
            print(f"Failed to list S3 objects: {e}")
            return []
        
        return examples
    
    def save_training_example(self, example_id: str, image_data: bytes, 
                            annotation: Dict[str, Any]) -> bool:
        """
        Save a training example to S3 cache.
        
        Args:
            example_id: Unique identifier for the example
            image_data: Raw image bytes
            annotation: Annotation data (rooms, doors, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Save image
            image_key = f"{self.cache_prefix}{example_id}.png"
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=image_key,
                Body=image_data,
                ContentType='image/png'
            )
            
            # Save annotation
            annotation_key = f"{self.cache_prefix}{example_id}.json"
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=annotation_key,
                Body=json.dumps(annotation, indent=2),
                ContentType='application/json'
            )
            
            return True
            
        except Exception as e:
            print(f"Failed to save training example {example_id}: {e}")
            return False
    
    def load_huggingface_dataset(self, max_examples: int = 20) -> List[Dict[str, Any]]:
        """
        Load examples from Hugging Face floor plans dataset.
        
        Args:
            max_examples: Maximum number of examples to load
            
        Returns:
            List of examples with image data
        """
        if not DATASETS_AVAILABLE:
            print("datasets library not available")
            return []
        
        try:
            # Load the dataset
            ds = load_dataset("OmarAmir2001/floor-plans-dataset", split='train')
            
            examples = []
            for i, item in enumerate(ds):
                if i >= max_examples:
                    break
                
                # Extract image
                if 'image' in item:
                    # Convert PIL Image to bytes
                    img = item['image']
                    buffer = BytesIO()
                    img.save(buffer, format='PNG')
                    image_data = buffer.getvalue()
                    
                    examples.append({
                        'id': f"hf_example_{i:03d}",
                        'image_data': image_data,
                        'metadata': {
                            'source': 'huggingface',
                            'dataset': 'OmarAmir2001/floor-plans-dataset',
                            'index': i
                        }
                    })
            
            return examples
            
        except Exception as e:
            print(f"Failed to load Hugging Face dataset: {e}")
            return []


# Global instance
_loader = None

def get_training_data_loader() -> TrainingDataLoader:
    """Get singleton training data loader instance."""
    global _loader
    if _loader is None:
        _loader = TrainingDataLoader()
    return _loader

