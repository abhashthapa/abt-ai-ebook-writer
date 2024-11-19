# E-Book Creator

This project is a command line Python application for creating e-books using AI agents. It generates table of content, content, designs cover pages for the book and each chapters, proofreads and exports into separate and merged MD and PDF files.

## Features

- Generate e-book content using AI
- Design cover pages with DALL-E 3
- Organize chapters through TOC and proofread content
- Export as a MD and PDF files

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/abhashthapa/ai-ebook-writer.git
   cd ai-ebook-writer
   ```

2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy the example environment file and fill in your API keys:
   ```bash
   cp .env.example .env
   ```

## Usage

Run the application:
```bash
python ebook_project.py
```
or use this if "python" did not work
```bash
ipython ebook_project.py
```
--

Follow the prompts to generate your e-book.


## License

This project is licensed under the MIT License.
