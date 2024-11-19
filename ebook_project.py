import os
from dotenv import load_dotenv
import requests
import textwrap
import openai

# Initialize cost tracking variables
total_tokens = 0
total_cost = 0.0

# Load environment variables from .env file
load_dotenv()

# Read the OpenAI API key
openai_api_key = os.getenv("OPENAI_API_KEY")
client = openai.Client(api_key=openai_api_key)

# Read the Tavily API key
tavily_api_key = os.getenv("TAVILY_API_KEY")

# Tavily and Crew.ai API configuration
tavily_api_url = "https://api.tavily.com/search"

# Custom Agent Classes

class DesignerAgent:
    def __init__(self):
        self.name = "Designer"
        self.role = "Generate cover page design"
        self.goal = "Create a relevant, minimal, and beautiful cover page using DALL-E 3"
        self.backstory = "Creative designer with a knack for generating stunning visuals"
        self.verbose = True
        self.llm = "dalle-3"
        self.allow_delegation = True
        self.tools = ["advanced_llm", "image_generation"]

    def generate_cover_prompt(self, book_title):
        prompt = f"Create an artwork design on subject '{book_title}'. The design should be minimal, beautiful, and relevant to the topic. The artwork should not be too imaginary. The artwork should not have actual book, book cover, book mockups and texts."
        return prompt

    def generate_chapter_prompt(self, chapter_title, chapter_summary):
        prompt = f"Create an artwork design for the chapter titled '{chapter_title}'. The design should be minimal, beautiful, and relevant to the topic. The artwork should not be too imaginary. The artwork should not have actual book, book cover, book mockups and texts. Here is a brief summary of the chapter: {chapter_summary}"
        return prompt


    def execute_task(self, book_title, toc, chapters):
        print(f"\n{self.name} is executing the task: Generating cover page design\n")
        cover_prompt = self.generate_cover_prompt(book_title)
        print(f"Prompt for DALL-E 3: {cover_prompt}")

        # Use DALL-E 3 to generate the cover page design
        completion_response = client.images.generate(
            model="dall-e-3",
            prompt=cover_prompt,
            n=1,
            size="1024x1024",
            quality="hd",
            style="vivid"
        )


        # Save the generated image
        image_url = completion_response.data[0].url
        image_response = requests.get(image_url)
        if image_response.status_code == 200:
            with open(f"{book_folder}/cover_page.png", "wb") as file:
                file.write(image_response.content)
            print(f"Cover page design saved as {book_folder}/cover_page.png")
        else:
            print("Failed to download the cover page design.")

        # Generate prompts and images for each chapter
        for chapter, summary in zip(chapters, chapter_summaries):
            chapter_title = chapter['title']
            chapter_prompt = self.generate_chapter_prompt(chapter_title, summary)
            print(f"Prompt for DALL-E 3: {chapter_prompt}")

            # Use DALL-E 3 to generate the chapter image
            completion_response = client.images.generate(
                model="dall-e-3",
                prompt=chapter_prompt,
                n=1,
                size="1024x1024",
                quality="hd",
                style="vivid"
            )

            # Save the generated image
            image_url = completion_response.data[0].url
            image_response = requests.get(image_url)
            if image_response.status_code == 200:
                with open(f"{book_folder}/{chapter_title.replace(' ', '_')}_image.png", "wb") as file:
                    file.write(image_response.content)
                print(f"Chapter image saved as {book_folder}/{chapter_title.replace(' ', '_')}_image.png")
            else:
                print(f"Failed to download the image for chapter: {chapter_title}")

class ProofreaderAgent:
    def __init__(self):
        self.name = "Proofreader"
        self.role = "Analyze content"
        self.goal = "Ensure no repeated content across chapters"
        self.backstory = "Expert in proofreading and content analysis"
        self.verbose = True
        self.llm = "gpt-4o"
        self.allow_delegation = True
        self.tools = ["advanced_llm", "text_analysis"]

    def execute_task(self, chapters):
        print(f"\n{self.name} is executing the task: Analyzing chapters for repeated content\n")
        # Combine all chapters into a single text for analysis, excluding book title and chapter titles
        combined_text = "\n\n".join([chapter['content'] for chapter in chapters])
        
        # Formulate the prompt for the LLM
        prompt = (
            "Analyze the following ebook content and identify any content that are repeated multiple times, making the book appear unprofessional and repetitive. Ignore the book title, chapter titles, and repetitive titles, however the actual content should not be repeated. Provide a list of such repeated topics or headings:\n\n"
            f"{combined_text}"
        )
        
        # Use the LLM to analyze the content
        completion_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000
        )
        
        # Track the cost for GPT-4 API call
        tokens_used = completion_response.usage.total_tokens
        cost = tokens_used * 0.03 / 1000  # Assuming $0.03 per 1,000 tokens for GPT-4
        global total_tokens, total_cost
        total_tokens += tokens_used
        total_cost += cost

        print(f"Tokens used: {tokens_used}, Cost: ${cost:.4f}")

        # Process the LLM's feedback
        repeated_content_feedback = completion_response.choices[0].message.content.strip()
        print(f"LLM Feedback on repeated content:\n{repeated_content_feedback}")
        
        # Extract repeated topics or headings from the LLM's feedback
        # Extract repeated topics or headings from the LLM's feedback
        repeated_content = [line.strip() for line in repeated_content_feedback.split('\n') if line.strip()]
        return repeated_content
class ResearcherAgent:
    def __init__(self, tavily_api_key):
        self.name = "Researcher"
        self.role = "Gather information"
        self.goal = "Collect and synthesize comprehensive and reliable data relevant to the ebook's topic"
        self.backstory = "Expert in data gathering and internet research, with a keen eye for detail"
        self.verbose = True
        self.llm = "gpt-4o"
        self.allow_delegation = True
        self.tools = ["advanced_llm", "web_access", "pdf_reader", "image_reader", "tavily_api"]
        self.tavily_api_key = tavily_api_key

    def execute_task(self, task):
        print(f"\n  \n{self.name} is executing the task: \n{task} \n  \n ")
        try:
            # Use Tavily API to gather information
            tavily_response = requests.post(
                tavily_api_url,
                headers={"Content-Type": "application/json"},
                json={"query": task, "api_key": self.tavily_api_key}
            )
            
            if tavily_response.status_code == 200:
                tavily_data = tavily_response.json()
                
                # Validate data
                research_data = self.validate_data(tavily_data)
                print(research_data)
                return research_data
            else:
                return f"Failed to gather information for {task}"
        except requests.exceptions.RequestException as e:
            return f"Error during API request: {e}"
    
    def validate_data(self, tavily_data):
        # Implement validation logic
        # For simplicity, we assume the data source returns a list of information
        # Assuming tavily_data is a dictionary with relevant keys
        validated_data = {
            "answer": tavily_data.get("answer", ""),
            "query": tavily_data.get("query", ""),
            "images": tavily_data.get("images", []),
            "results": tavily_data.get("results", []),
            "response_time": tavily_data.get("response_time", ""),
            "follow_up_questions": tavily_data.get("follow_up_questions", [])
        }
        return validated_data


class ContentOrganizerAgent:
    def __init__(self, tavily_api_key):
        self.tavily_api_key = tavily_api_key
        self.name = "Content Organizer"
        self.role = "Organize research data"
        self.goal = "Create a logical flow and structure for the ebook"
        self.backstory = "Skilled in organizing information and creating outlines"
        self.verbose = True
        self.llm = "gpt-4o"
        self.allow_delegation = True
        self.tools = ["advanced_llm", "text_structuring", "rag"]

    def execute_task(self, task):
        print(f" \n  \n{self.name} is executing the task: \n{task} \n  \n ")
        try:
            # Process research data to generate TOC
            research_summary = "\n".join([f"{key}: {value}" for key, value in task.items() if key in ["answer", "query", "results"]])
            toc_task = f"Create a TOC for an ebook about {task['query']} based on the following research data:\n{research_summary}. \n \nTable of contents should only have chapters, but no sub chapters or sections. Table of content should be systematic, should have high level topics and gradually increase the depth on the topic rather than a random list. Chapters should have CHAPTER 01 - Chapter name, CHAPTER 02 - Chapter name and so on as prefix. Do not include the text Table of contents as a chapter. Do not generate prefatory or introductory statements. Just show the output."
            completion_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": toc_task}
                ],
                max_tokens=1200
            )
            response_content = completion_response.choices[0].message.content.strip()

            # Track the cost for GPT-4 API call
            tokens_used = completion_response.usage.total_tokens
            cost = tokens_used * 0.03 / 1000  # Assuming $0.03 per 1,000 tokens for GPT-4
            global total_tokens, total_cost
            total_tokens += tokens_used
            total_cost += cost

            print(f"Tokens used: {tokens_used}, Cost: ${cost:.4f}")

            return response_content
        except requests.exceptions.RequestException as e:
            return f"Error during API request: {e}"


class WriterAgent:
    def __init__(self):
        self.name = "Writer"
        self.role = "Generate content"
        self.goal = "Write detailed and engaging content for each chapter"
        self.backstory = "Experienced writer with a flair for creating informative and captivating content"
        self.verbose = True
        self.llm = "gpt-4o"
        self.allow_delegation = True
        self.tools = ["advanced_llm", "text_writer"]
    
    def execute_task(self, task, research_data):
        # Simulate task execution with research data
        print(f" \n  \n{self.name} is executing the task: \n{task} \n  \n ")
        completion_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"{task} based on the following research data: {research_data}"}
            ],
            max_tokens=1200
        )
        response_content = completion_response.choices[0].message.content.strip()

        # Track the cost for GPT-4 API call
        tokens_used = completion_response.usage.total_tokens
        cost = tokens_used * 0.03 / 1000  # Assuming $0.03 per 1,000 tokens for GPT-4
        global total_tokens, total_cost
        total_tokens += tokens_used
        total_cost += cost

        print(f"Tokens used: {tokens_used}, Cost: ${cost:.4f}")

        return response_content


# Function to get user input with options
def get_user_input(prompt, options):
    while True:
        print(prompt)
        for i, option in enumerate(options, start=1):
            print(f"{i}. {option}")
        choice = input("Choose an option: ")
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        else:
            print("Invalid choice. Please try again.")


# Function to generate table of contents
def generate_toc(topic, content_organizer, research_data):
    # Extract relevant information from research data
    research_summary = "\n".join([f"{key}: {value}" for key, value in research_data.items() if key in ["answer", "query", "results"]])
    
    task = {
        "query": topic,
        "answer": research_data.get("answer", ""),
        "results": research_data.get("results", [])
    }
    toc_response = content_organizer.execute_task(task)
    return toc_response.split('\n')


# Function to generate chapter with specified format
def generate_chapter(chapter_title, writer, research_data, generate_images):
    print(f"Debug: research_data['query'] = {research_data['query']}")
    print(f"Debug: Research data for chapter '{chapter_title}': {research_data}")
    task = f"Write a detailed content for a book with chapter called '{chapter_title}' for this ebook about {research_data['query']}. Use simple and understandable English. Follow the research data and do not create imaginary content. Use your creative freedom, it is suggested but not important to divide it into structured segments similar to an academic book, including any relevant examples, facts, quotes, and notable people or brands only if applicable. Conduct research on the web to gather accurate information and provide references for any key points made. Each chapter should be around 750 to 1000 words. Use your creative freedom, it is suggested but not important that each segments might include the following elements, all or a few or even none: Start with an engaging introduction that provides a brief overview of the segment. Include practical examples to illustrate key points. Incorporate factual information and quotes from credible sources or notable figures. Mention notable people or brands related to the subject matter. Add a short exercise or interactive activity at the end to engage readers and reinforce learning. Provide references for all the key points made to ensure accuracy and credibility. End with a conclusion with a summary that recaps the main points discussed in the chapter. Make sure that you go through past and future topics from the table of contents so that there are no redundant content in this chapter. Do not add prefatory statements, your own status, notes, apologizes and inconvenience, like you don't have access to internet, feel free to adjust, I cannot provide direct reference from web, fact checking or follow ups like sure, here is a detailed structure for your book. Do not keep unended sentences. Do not generate any elements if you don't have enough information. Make the content print ready without any remarks or feedback from your side. Output should be a well formatted mark down for example H1 for Chapter title, H2, H3 and other headings for other segment titles."

    chapter_content = writer.execute_task(task, research_data)
    chapter_content = f"\n" + chapter_content.replace("```markdown", "").replace("```", "")
    chapter_image_path = f"{book_folder}/{chapter_title.replace(' ', '_')}_image.png"
    if generate_images:
        chapter_image_markdown = f"![{chapter_title} Image]({chapter_image_path})\n\n"
        chapter_content = chapter_image_markdown + chapter_content
    # Generate a summary for the chapter
    summary_task = f"Summarize the following chapter content in 2-3 sentences:\n\n{chapter_content}"
    chapter_summary = writer.execute_task(summary_task, research_data)
    return chapter_content, chapter_summary


def import_file(file_path):
    """Import data from a specified file."""
    try:
        with open(file_path, 'r') as file:
            data = file.read()
        print(f"Data imported from {file_path}")
        return data
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return None

# Main workflow
def main():
    global book_folder, toc, topic, chapter_summaries
    chapter_summaries = []
    # Step 1: Get the ebook topic
    topic = input("Enter the topic for the ebook (Min. 5 characters): ").strip()
    print("="*50 + "\n")
    book_folder = topic.replace(" ", "_")

    # Create directory for the ebook
    if not os.path.exists(book_folder):
        os.makedirs(book_folder)

    # Initialize agents with Tavily API key
    researcher = ResearcherAgent(tavily_api_key)
    content_organizer = ContentOrganizerAgent(tavily_api_key)
    writer = WriterAgent()
    proofreader = ProofreaderAgent()
    designer = DesignerAgent()

    # Research Information
    research_task = f"{topic}"
    research_data = researcher.execute_task(research_task)
    print("\n" + "="*50)
    print("Research data gathered successfully.")
    print(f"Debug: Full research_data = {research_data}")
    print("="*50 + "\n")

    # Step 2: Generate and review TOC
    toc = generate_toc(topic, content_organizer, research_data)
    while True:
        print("Table of Contents:")
        for item in toc:
            print(f"- {item}")
        action = input("\nType a number and hit enter to select an action: \n Accept = 1 \n Modify = 2 \n Regenerate = 3:\n ")
        if action.lower() == "1":
            break
        elif action.lower() == "2":
            print("\nEnter the modified TOC. Press Enter twice to finish:")
            toc_input = []
            while True:
                line = input()
                if line == "":
                    break
                toc_input.append(line)
            toc = toc_input
        elif action.lower() == "3":
            toc = generate_toc(topic, content_organizer, research_data)


    # Step 3.1: Ask user if they want to generate images
    generate_images = get_user_input(
        "\nDo you want to generate images for the chapters and cover page?",
        ["Yes", "No"]
    ) == "Yes"
    # Step 3.2: Ask user if they want a single long PDF or a chapter-broken PDF
    print("="*50 + "\n")
    pdf_generation_mode = get_user_input(
        "\nDo you want to generate a single long PDF or a chapter-broken PDF?",
        ["Single long PDF", "Chapter-broken PDF"]
    )

    # Step 3: Ask user if they want fast generation or review each chapter
    print("="*50 + "\n")
    generation_mode = get_user_input(
        "\nDo you want to continue with fast generation or review each chapter to continue?",
        ["Fast generation", "Review each chapter"]
    )

    if generation_mode == "Fast generation":
        # Generate all chapters without further prompts
        for chapter_title in toc:
            if "SECTION" in chapter_title.upper():
                continue  # Skip sections
            chapter_content, chapter_summary = generate_chapter(chapter_title, writer, research_data, generate_images)
            chapter_file = os.path.join(book_folder, f"{chapter_title.replace(' ', '_')}.md")
            with open(chapter_file, "w") as file:
                file.write(chapter_content)
            chapter_summaries.append(chapter_summary)
            print(f"\nGenerated and saved content for {chapter_title}")
            print("="*50 + "\n")
    else:
        print("="*50 + "\n")
        # Generate and review each chapter
        for chapter_title in toc:
            if "SECTION" in chapter_title.upper():
                continue  # Skip sections
            while True:
                chapter_content, chapter_summary = generate_chapter(chapter_title, writer, research_data, generate_images)
                print(f"Generated content for {chapter_title}:\n{chapter_content}")
                action = input(f"\nType a number and hit enter to select an action regarding the content for {chapter_title}? \n Accept = 1 \n Modify = 2 \n Regenerate = 3:\n ")
                if action.lower() == "1":
                    # Save chapter content to markdown file
                    chapter_file = os.path.join(book_folder, f"{chapter_title.replace(' ', '_')}.md")
                    with open(chapter_file, "w") as file:
                        file.write(chapter_content)
                    chapter_summaries.append(chapter_summary)
                    print(f"\nAccepted content for {chapter_title}")
                    print("="*50 + "\n")
                    break
                elif action.lower() == "2":
                    chapter_content = input(f"Enter the modified content for {chapter_title}: ")
                elif action.lower() == "3":
                    chapter_content, chapter_summary = generate_chapter(chapter_title, writer, research_data)

    # Step 4: Proofread chapters for repeated content
    print("="*50 + "\n")
    chapters = []
    for chapter_title in toc:
        if "SECTION" in chapter_title.upper():
            continue  # Skip sections
        chapter_file = os.path.join(book_folder, f"{chapter_title.replace(' ', '_')}.md")
        with open(chapter_file, "r") as file:
            chapter_content = file.read()
        chapters.append({"title": chapter_title, "content": chapter_content})

    while True:
        repeated_content = proofreader.execute_task(chapters)
        if not repeated_content:
            print("No repeated content found across chapters.")
            break

        user_choice = get_user_input(
            "\nDo you want to rewrite the repeated content?",
            ["Yes", "No"]
        )
        if user_choice.lower() == "no":
            break

        # Delegate rewriting to WriterAgent with full context for each repeated content
        for repeated in repeated_content:
            max_attempts = 3
            for chapter in chapters:
                if repeated in chapter['content']:
                    attempts = 0
                    while repeated in chapter['content'] and attempts < max_attempts:
                        print(f"Rewriting content for chapter: {chapter['title']} (Attempt {attempts + 1})")
                        print(f"Original repeated content: {repeated}")
                        # Provide full context to the WriterAgent
                        context = "\n\n".join([ch['content'] for ch in chapters])
                        full_book_context = "\n\n".join([ch['content'] for ch in chapters])
                        new_content = writer.execute_task(
                            f"Rewrite the following content to make it unique and remove redundancy. Do not add new sections or content:\n{repeated}\n\nFull Book Context:\n{full_book_context}",
                            research_data
                        )
                        chapter['content'] = chapter['content'].replace(repeated, new_content)
                        print(f"Rewritten content: {new_content}")
                        attempts += 1
                    if attempts == max_attempts:
                        print(f"Max rewrite attempts reached for chapter: {chapter['title']}. Skipping further rewrites.")
                    # Save the updated chapter content to markdown file
                    chapter_file = os.path.join(book_folder, f"{chapter['title'].replace(' ', '_')}.md")
                    with open(chapter_file, "w") as file:
                        file.write(chapter['content'])
        else:
            # Delegate rewriting to WriterAgent with full context for each repeated content
            for repeated in repeated_content:
                max_attempts = 3
                for chapter in chapters:
                    if repeated in chapter['content']:
                        attempts = 0
                        while repeated in chapter['content'] and attempts < max_attempts:
                            print(f"Rewriting content for chapter: {chapter['title']} (Attempt {attempts + 1})")
                            print(f"Original repeated content: {repeated}")
                            # Provide full context to the WriterAgent
                            context = "\n\n".join([ch['content'] for ch in chapters])
                            new_content = writer.execute_task(
                                f"Rewrite the following content to make it unique and remove redundancy:\n{repeated}\n\nContext:\n{context}",
                                research_data
                            )
                            chapter['content'] = chapter['content'].replace(repeated, new_content)
                            print(f"Rewritten content: {new_content}")
                            attempts += 1
                        if attempts == max_attempts:
                            print(f"Max rewrite attempts reached for chapter: {chapter['title']}. Skipping further rewrites.")
                        # Save the updated chapter content to markdown file
                        chapter_file = os.path.join(book_folder, f"{chapter['title'].replace(' ', '_')}.md")
                        with open(chapter_file, "w") as file:
                            file.write(chapter['content'])

    # Step 5: Generate cover page design if images are to be generated
    if generate_images:
        print("\n" + "="*50)
        designer.execute_task(topic, toc, chapters)
        print("="*50 + "\n")

    print("\n" + "="*50)
    print(f"Total tokens used: {total_tokens}")
    print(f"Total cost: ${total_cost:.4f}")
    print("="*50 + "\n")

    return book_folder, toc, topic, designer, writer, chapter_summaries, pdf_generation_mode, generate_images

def merge_chapters_into_single_file(book_folder, toc, book_title, designer, writer, generate_images):
    final_md_content = f"# {book_title}\n\n"
    if generate_images:
        final_md_content += f"![Cover Page]({book_folder}/cover_page.png)\n\n"
    final_md_content += f"### AUTHOR: {writer.llm}\n\n### DESIGNER: {designer.llm}\n\n## Table of Contents\n\n"
    for chapter_title in toc:
        if "SECTION" in chapter_title.upper():
            continue  # Skip sections
        final_md_content += f"- {chapter_title}\n"
    final_md_content += "\n"
    for chapter_title in toc:
        if "SECTION" in chapter_title.upper():
            continue  # Skip sections
        chapter_file = os.path.join(book_folder, f"{chapter_title.replace(' ', '_')}.md")
        with open(chapter_file, "r") as file:
            chapter_content = file.read()
            final_md_content += f"\n\n" + chapter_content + "\n\n"
    final_md_content += "Thank you for reading.\n"
    final_md_file = os.path.join(book_folder, f"{book_title.replace(' ', '_')}.md")
    with open(final_md_file, "w") as file:
        file.write(final_md_content)
    print(f"All chapters merged into {final_md_file}")
    return final_md_file
import subprocess
import os
from PyPDF2 import PdfMerger

def convert_md_to_pdf(md_file, pdf_file):
    try:
        print(f"Running command: markdown-pdf {md_file} -o {pdf_file}")
        result = subprocess.run(["markdown-pdf", md_file, "-o", pdf_file], check=True, capture_output=True, text=True)
        print(f"Subprocess output: {result.stdout}")
        print(f"Subprocess error (if any): {result.stderr}")
        print(f"Converted {md_file} to {pdf_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error converting {md_file} to PDF: {e}")

def merge_pdfs(pdf_files, output_pdf):
    merger = PdfMerger()
    for pdf in pdf_files:
        merger.append(pdf)
    merger.write(output_pdf)
    merger.close()
    print(f"Merged PDFs into {output_pdf}")

if __name__ == "__main__":
    book_folder, toc, topic, designer, writer, chapter_summaries, pdf_generation_mode, generate_images = main()

    # Generate cover page markdown
    cover_md_content = f"# {topic}\n\n![Cover Page]({book_folder}/cover_page.png)\n\n### AUTHOR: {writer.llm}\n\n### DESIGNER: {designer.llm}\n"
    cover_md_file = os.path.join(book_folder, "cover.md")
    with open(cover_md_file, "w") as file:
        file.write(cover_md_content)

    # Generate table of contents markdown
    toc_md_content = "## Table of Contents\n\n"
    for chapter_title in toc:
        if "SECTION" in chapter_title.upper():
            continue  # Skip sections
        toc_md_content += f"- {chapter_title}\n"
    toc_md_file = os.path.join(book_folder, "toc.md")
    with open(toc_md_file, "w") as file:
        file.write(toc_md_content)

    # Generate back cover markdown
    back_cover_md_content = "## Thank you for reading.\n"
    back_cover_md_file = os.path.join(book_folder, "back_cover.md")
    with open(back_cover_md_file, "w") as file:
        file.write(back_cover_md_content)

    if pdf_generation_mode == "Single long PDF":
        # Merge all markdown files into a single markdown file
        final_md_file = merge_chapters_into_single_file(book_folder, toc, topic, designer, writer, generate_images)
        # Convert the single markdown file to a PDF
        final_pdf_file = final_md_file.replace(".md", ".pdf")
        print("\n" + "="*50)
        convert_md_to_pdf(final_md_file, final_pdf_file)
        print("="*50 + "\n")
    else:
        # Convert markdown files to PDFs
        cover_pdf_file = cover_md_file.replace(".md", ".pdf")
        toc_pdf_file = toc_md_file.replace(".md", ".pdf")
        back_cover_pdf_file = back_cover_md_file.replace(".md", ".pdf")

        print("\n" + "="*50)
        convert_md_to_pdf(cover_md_file, cover_pdf_file)
        print("="*50 + "\n")
        print("\n" + "="*50)
        convert_md_to_pdf(toc_md_file, toc_pdf_file)
        print("="*50 + "\n")
        print("\n" + "="*50)
        convert_md_to_pdf(back_cover_md_file, back_cover_pdf_file)
        print("="*50 + "\n")

        chapter_pdf_files = []
        for chapter_title in toc:
            if "SECTION" in chapter_title.upper():
                continue  # Skip sections
            chapter_md_file = os.path.join(book_folder, f"{chapter_title.replace(' ', '_')}.md")
            chapter_pdf_file = chapter_md_file.replace(".md", ".pdf")
            print("\n" + "="*50)
            convert_md_to_pdf(chapter_md_file, chapter_pdf_file)
            print("="*50 + "\n")
            chapter_pdf_files.append(chapter_pdf_file)

        # Merge all PDFs into a single PDF
        all_pdfs = [cover_pdf_file, toc_pdf_file] + chapter_pdf_files + [back_cover_pdf_file]
        final_pdf_file = os.path.join(book_folder, f"{topic.replace(' ', '_')}.pdf")
        print("\n" + "="*50)
        merge_pdfs(all_pdfs, final_pdf_file)
        print("="*50 + "\n")
