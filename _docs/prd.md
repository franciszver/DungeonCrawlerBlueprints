
# DungeonCrawlerBlueprints_prd.md

## 1. Core Demo Goals
These are the must-have features to meet the original spec and deliver a compelling demo:
- **Upload Blueprint** (PNG/JPG) via React front-end.
- **Automatic Room Detection**: Bounding boxes drawn on the blueprint.
- **JSON Output**: Returned coordinates visible in a panel or console.
- **Confidence Scores**: Each detected room includes a confidence metric.
- **Processing Speed**: Results returned in <30 seconds.

---

## 2. High-Impact Enhancements (Demo Polish)
Lightweight features that make the product feel more complete:
- **Adjacency Graphs**: Show simple connectivity between rooms/hallways.
- **Semantic Label Hints**: Display suggested names (mocked or heuristic).
- **Export Options**: JSON and SVG overlay download.
- **Audit Metadata**: Show model version + processing time in output.

---

## 3. Hybrid AI Architecture (AWS + OpenRouter)
DungeonCrawlerBlueprints is built from the ground up to route tasks across multiple AI models:
- **AWS AI Services**:  
  - Rekognition or SageMaker for image processing.  
  - Textract for document parsing.  
  - CloudWatch for audit logging.  
- **OpenRouter Multi-Model Routing**:  
  - GPT-4 Vision for blueprint understanding.  
  - Claude or Gemini for semantic labeling and adjacency reasoning.  
  - Mistral or Mixtral for fast fallback or metadata generation.  
- **Routing Strategy**:  
  - Each task is routed to the most appropriate model.  
  - Model selection is logged for auditability and debugging.  
  - Contributors can configure routing via a simple schema:
    ```json
    {
      "task": "room_detection",
      "model": "gpt-4-vision",
      "fallback": "mistral"
    }
    ```

---

## 4. Technical Requirements
- **Cloud**: AWS (Lambda, API Gateway, S3).
- **AI Services**: OpenRouter + AWS AI/ML stack.
- **Frontend**: React for upload + visualization.
- **Performance**: <30s latency, ≥90% detection accuracy on test set.
- **Networking**: Public endpoints only (no VPC required for MVP).
- **Security**: IAM roles or API keys; CloudWatch logging for transparency.

---

## 5. Mock Data Strategy
- **Input**: Simplified JSON wall segments (normalized 0–1000).
- **Output**: Bounding boxes + confidence scores + optional adjacency.
- **Validation**: Rooms must be closed polygons; bounding boxes non-overlapping.
- **Note**: Doors/windows and load-bearing flags are out of scope for MVP.

---

## 6. Deliverables
- **Repo**: GitHub with README.md, API.md, MockData.md, Architecture.md.
- **Demo**: End-to-end flow (upload → detect → render → export).
- **Docs**: 1–2 page technical writeup + AI service configs.
- **Tests**: Basic unit tests for detection logic; integration demo required.

---

## 7. Roadmap (Post-Demo)
- **Phase 2**: Polygonal detection, richer adjacency graphs, semantic labeling.  
- **Phase 3**: Vector/PDF parsing, CAD export (DXF/SVG/IFC), multi-floor support.  
  - *Note*: Current version supports single-floor blueprints only. Multi-floor support is explicitly planned for future enterprise deployments.

---

## 8. Best Practices
### 8.1 Coordinate System
- Normalize all coordinates to a fixed range (0–1000).
- Origin convention: top-left (0,0), x increases to the right, y increases downward.
- Normalized values stored in JSON; conversion to real-world units can be added later.
- Validation: bounding boxes and polygons must be closed and non-overlapping.

### 8.2 Vector Inputs
- Parse only geometry layers relevant to walls/rooms; ignore annotations, text, or furniture layers in MVP.
- Convert vector line segments into graph nodes/edges; closed loops define rooms.
- Apply tolerance snapping (1–2 pixels) to avoid gaps in wall endpoints.
- Fallback: if vector parsing fails, rasterize the file and run the image-based pipeline.

### 8.3 General Practices
- Confidence scoring is required for every detected room.
- Partial results must be returned with error metadata if detection fails.
- Outputs must support adjacency graphs and semantic labels, even if MVP only fills bounding boxes.
- All outputs must be auditable: include model version, processing time, and detection metadata.
- Multi-floor support is not required for MVP, but explicitly planned for Phase 3 enterprise deployments.

---

## 9. Comparison & Evolution

### Alignment with Original Location Detection AI PRD
- **Same Core Goal**: Automate room boundary detection to save time and improve user experience.
- **Same Technical Foundation**: AWS cloud stack, React front-end, JSON outputs, <30s latency requirement.
- **Same Mock Data Strategy**: Simplified raster images + normalized JSON wall segments.

### Expansions in DungeonCrawlerBlueprints
- **Confidence Scoring**: Every room includes a confidence metric.
- **Adjacency Graphs**: Connectivity between rooms/hallways is modeled explicitly.
- **Semantic Hints**: Optional room labels (mocked, heuristic, or AI-generated).
- **Export Options**: JSON + SVG overlays, with CAD formats planned.
- **Audit Metadata**: Model version, processing time, error codes for compliance.
- **Contributor Onboarding**: README.md, API.md, MockData.md, Architecture.md for workflow hygiene.
- **Roadmap**: Clear phases (MVP → polygons/adjacency → enterprise multi-floor/CAD).

### Differentiator
- **Procedural Dynamic Room Generation (Game-Inspired)**:  
  DungeonCrawlerBlueprints draws on video game procedural map generation techniques (graph-based adjacency, flood-fill segmentation). This makes the system more adaptable to arbitrary blueprint styles and positions the product as both technically rigorous and creatively differentiated.

- **Built on AWS + OpenRouter from Day One**:  
  The project is architected to route tasks across multiple AI models, balancing cost, speed, and accuracy. This hybrid design enables modularity, auditability, and future extensibility—ideal for both demos and enterprise deployment.


