# Move all the workflow-related code (IELTSExerciseFlow, models, etc.) here
# Keep the imports and class definitions
# Remove the Streamlit-specific code 

import asyncio
from tavily import TavilyClient
from dotenv import load_dotenv
import os
from llama_index.core.workflow import (
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
    Context
)
import ell
import openai
from pydantic import BaseModel, Field
import fal_client

load_dotenv()

# Set up OpenAI client
client = openai.Client(api_key=os.getenv("OPENAI_API_KEY"))

# Event classes
class SubtopicPackage(Event):
    subtopic: str

class SubtopicSourceMaterialPackage(Event):
    subtopic_source_materials: str
    
class SourceMaterialPackage(Event):
    source_materials: str

class DraftEssayPackage(Event):
    draft_essay: str

class EditorCommentaryPackage(Event):
    editor_commentary: str
    
class FinalEssayPackage(Event):
    final_essay: str

class QuestionPackage(Event):
    questions: str

class ImagePackage(Event):
    image_url: str

# Pydantic models
class ContentSubtopics(BaseModel):
    subtopic_one: str = Field(description="First subtopic to research")
    subtopic_two: str = Field(description="Second subtopic to research")
    subtopic_three: str = Field(description="Third subtopic to research")

class IELTSEssay(BaseModel):
    title: str = Field(description="The title of the essay")
    introduction: str = Field(description="Introduction paragraph")
    body_paragraphs: list[str] = Field(description="List of body paragraphs")
    conclusion: str = Field(description="Conclusion paragraph")

class MultipleChoiceQuestion(BaseModel):
    question: str = Field(description="The multiple choice question")
    options: list[str] = Field(description="List of possible answers")
    answer: str = Field(description="The correct answer")

class TrueFalseQuestion(BaseModel):
    statement: str = Field(description="The true/false/not given statement")
    answer: str = Field(description="The answer (True, False, or Not Given)")

class IELTSQuestions(BaseModel):
    multiple_choice: list[MultipleChoiceQuestion] = Field(description="3 multiple choice questions")
    true_false: list[TrueFalseQuestion] = Field(description="4 true/false/not given statements")
    matching_headings: list[str] = Field(description="4 paragraph headings")

class IELTSExerciseFlow(Workflow):
    @step
    async def research_source_materials(self, ctx: Context, ev: StartEvent) -> SourceMaterialPackage:
        topic = ev.query
        print(f'topic: {topic}')
        await ctx.set('topic', topic)

        tavily_client = TavilyClient()
        response = tavily_client.search(topic)
        source_materials = '\n'.join(result['content'] for result in response['results'])
        await ctx.set('source_materials', source_materials)

        @ell.complex(model="gpt-4o-mini", client=client, response_format=ContentSubtopics)
        def generate_subtopics(topic: str, materials: str) -> ContentSubtopics:
            """You are a research assistant identifying key subtopics."""
            return f"Based on these materials about {topic}, identify 3 distinct subtopics: {materials}"

        message = generate_subtopics(topic, source_materials)
        subtopics = message.parsed
        
        # Research each subtopic
        additional_materials = []
        for subtopic in [subtopics.subtopic_one, subtopics.subtopic_two, subtopics.subtopic_three]:
            subtopic_response = tavily_client.search(subtopic)
            subtopic_materials = '\n'.join(result['content'] for result in subtopic_response['results'])
            additional_materials.append(subtopic_materials)
        
        all_materials = source_materials + "\n\n" + "\n\n".join(additional_materials)
        return SourceMaterialPackage(source_materials=all_materials)

    @step
    async def write_essay(self, ctx: Context, ev: SourceMaterialPackage) -> DraftEssayPackage:
        topic = await ctx.get('topic')
        source_materials = ev.source_materials

        @ell.complex(model="gpt-4o-mini", client=client, response_format=IELTSEssay)
        def write_ielts_essay(topic: str, materials: str) -> IELTSEssay:
            """You are an expert IELTS essay writer."""
            return f"""Write a short formal academic essay about {topic} using these materials.
                    
                    Requirements:
                    - Keep it concise (300-400 words)
                    - Include a brief introduction
                    - 2-3 short body paragraphs
                    - Brief conclusion
                    - Use academic language but keep it clear
                    - Include key facts from the materials
                    
                    Materials: {materials}"""

        message = write_ielts_essay(topic, source_materials)
        essay = message.parsed
        
        formatted_essay = f"# {essay.title}\n\n{essay.introduction}\n\n"
        formatted_essay += "\n\n".join(essay.body_paragraphs)
        formatted_essay += f"\n\n{essay.conclusion}"
        
        await ctx.set('draft_essay', formatted_essay)
        return DraftEssayPackage(draft_essay=formatted_essay)

    @step
    async def refine_draft_essay(self, ctx: Context, ev: DraftEssayPackage) -> EditorCommentaryPackage:
        print('editor reviewing draft essay')
        topic = await ctx.get('topic')
        draft_essay = ev.draft_essay
        
        @ell.simple(model="gpt-4o-mini", client=client)
        def review_essay(topic: str, essay: str) -> str:
            """You are an IELTS examiner reviewing essays."""
            return f"""Review this IELTS essay about {topic}: {essay}
                   Suggest improvements for:
                   - Academic language use
                   - Paragraph structure
                   - Clarity of arguments
                   - Factual content
                   Write in md syntax"""

        response = review_essay(topic, draft_essay)
        return EditorCommentaryPackage(editor_commentary=str(response))

    @step
    async def write_final_essay(self, ctx: Context, ev: EditorCommentaryPackage) -> FinalEssayPackage:
        print('finalizing essay')
        topic = await ctx.get('topic')
        editor_commentary = ev.editor_commentary
        draft_essay = await ctx.get('draft_essay')

        @ell.simple(model="gpt-4o-mini", client=client)
        def refine_essay(topic: str, draft: str, commentary: str) -> str:
            """You are an expert IELTS essay editor."""
            return f"""Refine this essay about {topic} based on the editor's comments:

                   Draft essay: {draft}
                   Editor's comments: {commentary}

                   Make it more suitable for IELTS reading test.
                   Ensure academic tone, clear structure, and factual accuracy.
                   Output only the refined essay, no commentary."""

        final_essay = refine_essay(topic, draft_essay, editor_commentary)
        
        with open('publication/final_essay.md', 'w', encoding='utf-8') as f:
            f.write(str(final_essay))
        return FinalEssayPackage(final_essay=str(final_essay))

    @step
    async def generate_illustration(self, ctx: Context, ev: FinalEssayPackage) -> ImagePackage:
        print('generating illustration')
        topic = await ctx.get('topic')
        essay = ev.final_essay

        @ell.simple(model="gpt-4o-mini", client=client)
        def create_image_prompt(topic: str, essay: str) -> str:
            """You are an expert at writing prompts for AI image generation."""
            return f"""Create a detailed image generation prompt for this academic essay about {topic}.
                   The image should be professional and educational.
                   Essay: {essay}
                   
                   Write only the image prompt, no other text."""

        prompt = create_image_prompt(topic, essay)

        result = fal_client.subscribe(
            "fal-ai/flux-pro/v1.1-ultra",
            arguments={
                "prompt": prompt
            }
        )

        image_url = result['images'][0]['url']
        await ctx.set('image_url', image_url)
        return ImagePackage(image_url=image_url)

    @step
    async def generate_questions(self, ctx: Context, ev: FinalEssayPackage | ImagePackage) -> StopEvent:
        """Modified to accept either FinalEssayPackage or ImagePackage"""
        if isinstance(ev, ImagePackage):
            # Store the image URL in context if it comes from ImagePackage
            await ctx.set('image_url', ev.image_url)
            return None
            
        print('generating IELTS questions')
        final_essay = ev.final_essay

        @ell.complex(model="gpt-4o-mini", client=client, response_format=IELTSQuestions)
        def create_ielts_questions(essay: str) -> IELTSQuestions:
            """You are an IELTS test creator generating reading comprehension questions."""
            return f"""Create IELTS reading comprehension questions for this essay:
                    {essay}
                    
                    Generate:
                    - 3 multiple choice questions with 4 options each
                    - 4 true/false/not given statements
                    - 4 paragraph headings"""

        message = create_ielts_questions(final_essay)
        questions = message.parsed
        
        # Format questions in markdown with data attributes for interactivity
        formatted_questions = "# IELTS Reading Questions\n\n"
        
        # Multiple Choice section
        formatted_questions += "## Multiple Choice Questions\n\n"
        formatted_questions += '<div class="question-section" id="multiple-choice">\n'
        for i, q in enumerate(questions.multiple_choice, 1):
            formatted_questions += f'<div class="question" data-type="multiple-choice" data-id="{i}">\n'
            formatted_questions += f"{i}. {q.question}\n"
            for j, opt in enumerate(q.options):
                formatted_questions += f'<label class="option"><input type="radio" name="mc-{i}" value="{opt}"> {opt}</label>\n'
            formatted_questions += '</div>\n\n'
        formatted_questions += '</div>\n\n'
        
        # True/False section
        formatted_questions += "## True/False/Not Given\n\n"
        formatted_questions += '<div class="question-section" id="true-false">\n'
        for i, q in enumerate(questions.true_false, 1):
            formatted_questions += f'<div class="question" data-type="true-false" data-id="{i}">\n'
            formatted_questions += f"{i}. {q.statement}\n"
            formatted_questions += f'''<label class="option"><input type="radio" name="tf-{i}" value="True"> True</label>
                <label class="option"><input type="radio" name="tf-{i}" value="False"> False</label>
                <label class="option"><input type="radio" name="tf-{i}" value="Not Given"> Not Given</label>
            </div>\n\n'''
        formatted_questions += '</div>\n\n'
        
        # Matching Headings section
        formatted_questions += "## Matching Headings\n\n"
        formatted_questions += '<div class="question-section" id="matching">\n'
        formatted_questions += "Match these headings to the correct paragraphs:\n\n"
        formatted_questions += '<div class="matching-container">\n'
        formatted_questions += '<div class="headings-list">\n'
        for i, heading in enumerate(questions.matching_headings, 1):
            formatted_questions += f'<div class="heading" draggable="true" data-id="{i}">{heading}</div>\n'
        formatted_questions += '</div>\n'
        formatted_questions += '<div class="paragraph-slots">\n'
        for i in range(len(questions.matching_headings)):
            formatted_questions += f'<div class="slot" data-slot="{i+1}">Paragraph {i+1}</div>\n'
        formatted_questions += '</div>\n</div>\n</div>\n\n'
        
        # Hidden answer key (will be revealed after submission)
        formatted_questions += '<div id="answer-key" class="hidden">\n'
        formatted_questions += '<div class="answer-key-container">\n'
        formatted_questions += '<h2 class="text-xl font-bold mb-4">Answer Key</h2>\n'
        
        # Multiple Choice answers
        formatted_questions += '<div class="answer-section">\n'
        formatted_questions += '<h3 class="font-semibold mb-2">Multiple Choice Questions</h3>\n'
        for i, q in enumerate(questions.multiple_choice, 1):
            formatted_questions += f'<div class="answer-item" data-answer-type="mc" data-id="{i}">\n'
            formatted_questions += f'<span class="question-number">Question {i}</span>&nbsp;{q.answer}\n'
            formatted_questions += '</div>\n'
        formatted_questions += '</div>\n'
        
        # True/False answers
        formatted_questions += '<div class="answer-section">\n'
        formatted_questions += '<h3 class="font-semibold mb-2">True/False/Not Given</h3>\n'
        for i, q in enumerate(questions.true_false, 1):
            formatted_questions += f'<div class="answer-item" data-answer-type="tf" data-id="{i}">\n'
            formatted_questions += f'<span class="question-number">Statement {i}</span>&nbsp;{q.answer}\n'
            formatted_questions += '</div>\n'
        formatted_questions += '</div>\n'
        
        # Matching answers
        formatted_questions += '<div class="answer-section">\n'
        formatted_questions += '<h3 class="font-semibold mb-2">Matching Headings</h3>\n'
        formatted_questions += '<div class="matching-answers">\n'
        for i, heading in enumerate(questions.matching_headings, 1):
            formatted_questions += f'<div class="answer-item">Paragraph {i}: {heading}</div>\n'
        formatted_questions += '</div>\n'
        formatted_questions += '</div>\n'
        
        formatted_questions += '</div>\n</div>\n\n'
        
        # Add submit button and score display
        formatted_questions += '<div class="controls-container">\n'
        formatted_questions += '<button id="submit-answers" class="submit-btn">Submit Answers</button>\n'
        formatted_questions += '<button id="try-again" class="try-again-btn hidden">Try Again</button>\n'
        formatted_questions += '<div id="score-display" class="hidden"></div>\n'
        formatted_questions += '</div>\n'

        with open('publication/questions.md', 'w', encoding='utf-8') as f:
            f.write(formatted_questions)
            
        # Get the image URL that was stored earlier
        image_url = await ctx.get('image_url')
            
        return StopEvent(result={
            "status": "Exercise generation completed successfully",
            "image_url": image_url
        })

    # Add workflow steps configuration
    def configure_steps(self):
        return {
            "research_source_materials": {},
            "write_essay": {"input_steps": ["research_source_materials"]},
            "refine_draft_essay": {"input_steps": ["write_essay"]},
            "write_final_essay": {"input_steps": ["refine_draft_essay"]},
            "generate_illustration": {"input_steps": ["write_final_essay"]},
            "generate_questions": {
                "input_steps": ["write_final_essay", "generate_illustration"]
            }
        }

# Helper function to read markdown files
def read_markdown_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None

# Function to generate exercise
async def generate_exercise(topic):
    os.makedirs('publication', exist_ok=True)
    w = IELTSExerciseFlow(timeout=10000, verbose=False)
    result = await w.run(query=topic)
    
    # Get image URL from the result
    image_url = None
    if isinstance(result, dict):
        image_url = result.get('image_url')
    
    return {
        'result': result,
        'image_url': image_url
    } 