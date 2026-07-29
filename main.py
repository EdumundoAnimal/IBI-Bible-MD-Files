import os
import glob
import time
import json
import re
import subprocess
from typing import List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import APIError


# =====================================================================
# 1. STRUCTURAL SCHEMAS
# =====================================================================
class EvidenceQuote(BaseModel):
   quote: str = Field(description="The exact verbatim quote from the text.")
   context: str = Field(description="The page, chapter, or section source.")


class ThematicBreakdown(BaseModel):
   concept_name: str = Field(description="The major or minor concept.")
   description: str = Field(description="Analytical explanation of core arguments.")


class DocumentAnalysisSchema(BaseModel):
   article_title: str = Field(description="The clean title or name of the document/article. Keep short.")
   author_name: str = Field(description="The name of the author or creator of the text. Use 'Unknown' if none.")
   ocr_cleaned_text: str = Field(description="Systematic OCR layout cleanup of raw body content.")
   extracted_tables_csv: List[str] = Field(
       description="Reconstructed tables represented strictly as clean CSV strings.")
   themes: List[ThematicBreakdown] = Field(description="Array of arguments, patterns, and concepts.")
   evidence_mapping: List[EvidenceQuote] = Field(description="Key sentences preserved as true verbatim strings.")


# =====================================================================
# 2. STRING SANITIZATION & ENGINE UTILITIES
# =====================================================================
def generate_safe_filename(title: str, author: str) -> str:
   """Combines metadata elements into a clean, snake_case legal string."""
   combined = f"{title}_{author}"
   clean_chars = re.sub(r"[^\w\s-]", "", combined)
   snake_case = re.sub(r"[\s-]+", "_", clean_chars)
   return re.sub(r"_+", "_", snake_case).strip("_").lower()


def compile_markdown_document(data: DocumentAnalysisSchema, focus: str) -> str:
   """
   Assembles structured properties into a Markdown text string complete
   with standard compliant YAML frontmatter blocks optimized for Obsidian.
   """
   current_date = time.strftime('%Y-%m-%d')

   # Generate clean tag list from industry focus definitions
   clean_tag = re.sub(r"[^\w\s]", "", focus).strip().replace(" ", "/").lower()

   md = []

   # --- START YAML FRONTMATTER ---
   md.append("---")
   md.append(f"title: \"{data.article_title.replace('\"', '\\\"')}\"")
   md.append(f"author: \"{data.author_name.replace('\"', '\\\"')}\"")
   md.append(f"processed_date: {current_date}")
   md.append("type: literature-note")
   md.append("tags:")
   md.append(f"  - document-pipeline/{clean_tag}")
   md.append(f"  - author/{generate_safe_filename('', data.author_name)}")
   md.append("aliases:")
   md.append(f"  - \"{data.article_title}\"")
   md.append("---")
   # --- END YAML FRONTMATTER ---

   md.append(f"\n# {data.article_title}")
   md.append(f"**Author:** [[{data.author_name}]]\n")

   md.append("## 1. Cleaned Document Text")
   md.append(f"{data.ocr_cleaned_text.strip()}\n")

   if data.extracted_tables_csv:
       md.append("## 2. Quantitative Metric Tables")
       for idx, table in enumerate(data.extracted_tables_csv):
           md.append(f"### Table {idx + 1}\n```csv\n{table.strip()}\n```\n")

   md.append("## 3. Thematic Analysis Matrices")
   for theme in data.themes:
       md.append(f"### Theme: {theme.concept_name}\n{theme.description}\n")

   md.append("## 4. Evidence Matrix & Verbatim Assertions")
   for mapping in data.evidence_mapping:
       md.append(f"> \"{mapping.quote}\"\n*Context Source: {mapping.context}*\n")

   return "\n".join(md)


# =====================================================================
# 3. GIT SYNCHRONIZATION BACKEND SERVICE
# =====================================================================
def sync_workspace_to_github(target_directory: str, repo_url: str):
   """Automates repository management and sync engines out to cloud setups."""
   print(r"\n[Git Sync] Initializing validation sweeps inside target folder: {C:\Users\eparkes\PycharmProjects\PythonProject}")

   def run_git_cmd(args: List[str]):
       result = subprocess.run(
           args, cwd=target_directory, capture_output=True, text=True, check=True
       )
       return result.stdout.strip()

   try:
       if not os.path.exists(os.path.join(target_directory, ".git")):
           print("[Git Sync] Repository mapping missing locally. Instantiating git layout...")
           run_git_cmd(["git", "init"])
           run_git_cmd(["git", "checkout", "-b", "main"])
           run_git_cmd(["git", "remote", "add", "origin", repo_url])
       else:
           print("[Git Sync] Valid repository mapping recognized. Checking current configuration...")
           try:
               run_git_cmd(["git", "remote", "set-url", "origin", repo_url])
           except subprocess.CalledProcessError:
               run_git_cmd(["git", "remote", "add", "origin", repo_url])

       try:
           print("[Git Sync] Running upstream delta checks (git fetch)...")
           run_git_cmd(["git", "fetch", "origin", "main"])
           run_git_cmd(["git", "rebase", "origin/main"])
       except subprocess.CalledProcessError:
           print("[Git Sync] No active head found on remote branch, initializing tracking updates...")

       print("[Git Sync] Staging updated analytical files...")
       run_git_cmd(["git", "add", "."])

       status = run_git_cmd(["git", "status", "--porcelain"])
       if not status:
           print("[Git Sync] No layout variations caught by tracker. Workspace is clean.")
           return

       commit_msg = f"Automated structural pipeline synchronization: {time.strftime('%Y-%m-%d %H:%M:%S')}"
       print(f"[Git Sync] Packing adjustments: '{commit_msg}'")
       run_git_cmd(["git", "commit", "-m", commit_msg])

       print(r"[Git Sync] Shipping local assets out to remote cluster: {https://github.com/EdumundoAnimal/IBI-Bible-MD-Files}")
       run_git_cmd(["git", "push", "-u", "origin", "main"])
       print("[Git Sync] System payload synchronization successful.")

   except subprocess.CalledProcessError as e:
       print(f"[Git Sync Error] System level orchestration tracking failed.")
       print(f"Command executed: {' '.join(e.cmd)}")
       print(f"Tracking error trace log:\n{e.stderr.strip()}")
   except Exception as general_git_err:
       print(f"[Git Sync Error] Critical execution error safely intercepted: {general_git_err}")


# =====================================================================
# 4. CORE PIPELINE CONTROLLER
# =====================================================================
def execute_batch_processing_pipeline(input_dir: str, output_dir: str, focus: str, repo_url: str):
   """Processes directory targets, writes markdown data, and triggers the sync service."""
   # Ensure your GEMINI_API_KEY environment variable is set before running
   client = genai.Client()
   os.makedirs(output_dir, exist_ok=True)

   targets = glob.glob(os.path.join(input_dir, "*.pdf"))
   if not targets:
       print(f"Pipeline Stopped: No input files discovered within directory structure: {input_dir}")
       return

   print(f"Found {len(targets)} PDFs to process...")

   for pdf_path in targets:
       print(f"\nProcessing: {os.path.basename(pdf_path)}...")
       try:
           # 1. Upload file to Gemini API
           uploaded_file = client.files.upload(file=pdf_path)

           # Wait for file processing if necessary (recommended for large PDFs)
           while uploaded_file.state.name == "PROCESSING":
               print("Waiting for file processing...")
               time.sleep(2)
               uploaded_file = client.files.get(name=uploaded_file.name)

           # 2. Query Gemini using the structured schema response framework
           prompt = f"Analyze this document thoroughly according to the required schema. Focus area: {focus}"
           response = client.models.generate_content(
               model='gemini-3.1-flash-lite',  # Or your preferred Gemini model
               contents=[uploaded_file, prompt],
               config=types.GenerateContentConfig(
                   response_mime_type="application/json",
                   response_schema=DocumentAnalysisSchema,
               ),
           )

           # 3. Parse JSON results matching DocumentAnalysisSchema
           json_data = json.loads(response.text)
           structured_data = DocumentAnalysisSchema(**json_data)

           # 4. Generate Markdown structure with YAML Frontmatter
           markdown_content = compile_markdown_document(structured_data, focus)

           # 5. Save final file locally
           safe_filename = generate_safe_filename(structured_data.article_title, structured_data.author_name)
           output_file_path = os.path.join(output_dir, f"{safe_filename}.md")

           with open(output_file_path, "w", encoding="utf-8") as f:
               f.write(markdown_content)

           print(f"Successfully generated: {output_file_path}")

           # Clean up the file from Gemini cloud storage
           client.files.delete(name=uploaded_file.name)

       except APIError as api_err:
           print(f"Gemini API Error processing {os.path.basename(pdf_path)}: {api_err}")
       except Exception as e:
           print(f"Failed to process {os.path.basename(pdf_path)}: {str(e)}")

   # Trigger Git synchronization after processing all files
   sync_workspace_to_github(target_directory=output_dir, repo_url=repo_url)


# =====================================================================
# 5. EXECUTION ENTRYPOINT
# =====================================================================
if __name__ == "__main__":
   # Define your local pipeline parameters here
   INPUT_PDF_DIR = r"C:\Users\eparkes\Desktop\pdfs"
   OUTPUT_MD_DIR = r"C:\Users\eparkes\PycharmProjects\PythonProject"
   INDUSTRY_FOCUS = "Bible Study Analysis"
   GITHUB_REPO_URL = "https://github.com/EdumundoAnimal/IBI-Bible-MD-Files"

   execute_batch_processing_pipeline(
       input_dir=INPUT_PDF_DIR,
       output_dir=OUTPUT_MD_DIR,
       focus=INDUSTRY_FOCUS,
       repo_url=GITHUB_REPO_URL
   )

