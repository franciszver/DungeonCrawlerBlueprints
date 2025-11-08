
# Architecture.md — DungeonCrawlerBlueprints

flowchart TD
  A[User] --> B[React Frontend]
  B --> C[API Gateway]
  C --> D[AWS Lambda]
  D --> E[Detection Pipeline]
  E --> F1[OpenRouter]
  E --> F2[AWS AI Services]
  E --> G[S3 Storage]
  D --> H[CloudWatch Logging]
  B --> I[Results Viewer / Export Panel]

  subgraph Frontend
    B
    I
  end

  subgraph AWS
    C
    D
    G
    H
    F2[Rekognition / SageMaker / Textract]
  end

  subgraph OpenRouter
    F1_GPT4[GPT-4 Vision]
    F1_Claude[Claude / Gemini]
    F1_Mistral[Mistral / Mixtral]
    F1 --> F1_GPT4
    F1 --> F1_Claude
    F1 --> F1_Mistral
  end

  subgraph Detection Pipeline
    E1[Image Input → GPT-4 Vision]
    E2[Vector Input → Graph Parser]
    E3[Semantic Labeling → Claude/Gemini]
    E4[Adjacency Graph → Mixtral/Claude]
    E --> E1
    E --> E2
    E --> E3
    E --> E4
  end

  G --> J[Export: JSON / SVG]
  H --> K[Audit Logs: Model, Time, Version]

  style A fill:#f9f,stroke:#333,stroke-width:1px
  style B fill:#bbf,stroke:#333,stroke-width:1px
  style C fill:#ccf,stroke:#333,stroke-width:1px
  style D fill:#ccf,stroke:#333,stroke-width:1px
  style E fill:#cfc,stroke:#333,stroke-width:1px
  style F1 fill:#ffc,stroke:#333,stroke-width:1px
  style F2 fill:#ffc,stroke:#333,stroke-width:1px
  style G fill:#fcf,stroke:#333,stroke-width:1px
  style H fill:#eee,stroke:#333,stroke-width:1px
  style I fill:#bbf,stroke:#333,stroke-width:1px
  style J fill:#fff,stroke:#333,stroke-width:1px
  style K fill:#eee,stroke:#333,stroke-width:1px

