sequenceDiagram
    participant Start
    participant Research
    participant Essay
    participant Editor
    participant Final
    participant Image
    participant Questions

    Start->>Research: StartEvent(topic)
    
    Research->>Research: Tavily search topic
    Research->>Research: Generate subtopics
    
    par Research Subtopics
        Research->>Research: Search subtopic 1
        Research->>Research: Search subtopic 2
        Research->>Research: Search subtopic 3
    end
    
    Research-->>Essay: SourceMaterialPackage

    Essay->>Essay: Generate draft essay
    Essay-->>Editor: DraftEssayPackage

    Editor->>Editor: Review and suggest improvements
    Editor-->>Final: EditorCommentaryPackage

    Final->>Final: Refine essay
    Final->>FileSystem: Save final_essay.md
    
    par Parallel Steps
        Final-->>Image: FinalEssayPackage
        Final-->>Questions: FinalEssayPackage
    end

    Image->>Image: Generate image prompt
    Image->>Image: Call fal-ai API
    Image-->>Questions: ImagePackage

    Questions->>Questions: Generate IELTS questions
    Questions->>FileSystem: Save questions.md
    Questions-->>Stop: StopEvent(result, image_url)

    Note over Research,Questions: Workflow Steps Configuration:
    Note over Research,Questions: research_source_materials: {}
    Note over Research,Questions: write_essay: {input: research_source_materials}
    Note over Research,Questions: refine_draft_essay: {input: write_essay}
    Note over Research,Questions: write_final_essay: {input: refine_draft_essay}
    Note over Research,Questions: generate_illustration: {input: write_final_essay}
    Note over Research,Questions: generate_questions: {input: [write_final_essay, generate_illustration]}

1. Research phase:
   - Topic search
   - Subtopic generation
   - Detailed research

2. Content generation:
   - Essay writing
   - Editorial review
   - Final refinement

3. Multimedia:
   - Image generation
   - Audio creation

4. Exercise creation:
   - Question generation
   - Answer key creation 