import json
import logging
from pathlib import Path
from typing import Iterator, Optional, Tuple
import asyncio

import gradio as gr
import httpx

logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
DEFAULT_MODEL = "llama3.2:1b"
AVAILABLE_CATEGORIES = ["github_advisory", "uploaded"]


async def upload_pdf_handler(file_path: Optional[str]) -> str:
    """Upload a PDF file to the RAG system"""
    if not file_path:
        return "❌ No file selected"

    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return "❌ File not found"

        if not file_path.suffix.lower() == ".pdf":
            return "❌ Please upload a PDF file"

        # Read file as bytes
        with open(file_path, "rb") as f:
            file_content = f.read()

        # Upload via API
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"file": (file_path.name, file_content, "application/pdf")}
            response = await client.post(f"{API_BASE_URL}/upload/", files=files)

            if response.status_code == 201:
                data = response.json()
                upload_id = data.get("upload_id")
                filename = data.get("filename")
                return f"✅ Upload successful!\n\n📄 **{filename}**\n🆔 Upload ID: `{upload_id}`\n\nProcessing your PDF... Use the ID above to check status."
            else:
                error_detail = response.json().get("detail", "Unknown error")
                return f"❌ Upload failed: {error_detail}"

    except httpx.RequestError as e:
        return f"❌ Connection error: {str(e)}\nMake sure the API server is running at {API_BASE_URL}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


async def check_upload_status(upload_id: str) -> str:
    """Check the processing status of an uploaded PDF"""
    if not upload_id.strip():
        return "Please enter an upload ID"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE_URL}/upload/{upload_id.strip()}")

            if response.status_code == 200:
                data = response.json()
                status = data.get("processing_status", "unknown")
                filename = data.get("filename", "Unknown")
                title = data.get("title")
                authors = data.get("authors")
                error_msg = data.get("error_message")

                # Status emoji mapping
                status_emoji = {"pending": "⏳", "processing": "⚙️", "completed": "✅", "failed": "❌"}

                result = f"{status_emoji.get(status, '❓')} **Status: {status.upper()}**\n\n"
                result += f"📄 **Filename:** {filename}\n"

                if title:
                    result += f"📝 **Title:** {title}\n"
                if authors:
                    result += f"✍️ **Authors:** {', '.join(authors) if isinstance(authors, list) else authors}\n"
                if error_msg:
                    result += f"\n❌ **Error:** {error_msg}\n"

                if status == "completed":
                    result += "\n🎉 Your PDF is ready! You can now ask questions about it using the chat interface."
                elif status == "processing":
                    result += "\n⏳ Processing in progress... Check back in a few moments."
                elif status == "pending":
                    result += "\n⏳ Your upload is queued for processing."

                return result
            elif response.status_code == 404:
                return f"❌ Upload ID not found: {upload_id}"
            else:
                return f"❌ Error: API returned status {response.status_code}"

    except httpx.RequestError as e:
        return f"❌ Connection error: {str(e)}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


async def process_upload_handler(upload_id: str) -> str:
    """Trigger processing of an uploaded PDF"""
    if not upload_id.strip():
        return "Please enter an upload ID"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{API_BASE_URL}/upload/{upload_id.strip()}/process")

            if response.status_code == 200:
                data = response.json()
                chunks_indexed = data.get("chunks_indexed", 0)
                metadata = data.get("metadata", {})
                title = metadata.get("title", "Unknown")

                return f"✅ Processing complete!\n\n📄 **Title:** {title}\n📊 **Chunks indexed:** {chunks_indexed}\n\n🎉 Your PDF is ready for questions!"
            elif response.status_code == 400:
                error_detail = response.json().get("detail", "Unknown error")
                return f"⚠️ {error_detail}"
            elif response.status_code == 404:
                return f"❌ Upload ID not found: {upload_id}"
            else:
                error_detail = response.json().get("detail", "Unknown error")
                return f"❌ Processing failed: {error_detail}"

    except httpx.RequestError as e:
        return f"❌ Connection error: {str(e)}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


async def list_uploads_handler() -> str:
    """List all uploaded PDFs"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE_URL}/uploads/?limit=20")

            if response.status_code == 200:
                data = response.json()
                total = data.get("total", 0)
                uploads = data.get("uploads", [])

                if total == 0:
                    return "📁 No uploads yet. Upload your first PDF above!"

                result = f"📚 **Your Uploads** (showing {len(uploads)} of {total})\n\n"

                for upload in uploads:
                    status = upload.get("processing_status", "unknown")
                    filename = upload.get("filename", "Unknown")
                    upload_id = upload.get("upload_id", "")
                    title = upload.get("title", "No title")

                    status_emoji = {"pending": "⏳", "processing": "⚙️", "completed": "✅", "failed": "❌"}

                    result += f"{status_emoji.get(status, '❓')} **{filename}**\n"
                    result += f"   ID: `{upload_id}`\n"
                    result += f"   Status: {status}\n"
                    if status == "completed" and title != "No title":
                        result += f"   Title: {title}\n"
                    result += "\n"

                return result
            else:
                return f"❌ Error: API returned status {response.status_code}"

    except httpx.RequestError as e:
        return f"❌ Connection error: {str(e)}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


async def get_completed_pdfs() -> Tuple[list, dict]:
    """Get list of completed PDFs for dropdown selection"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE_URL}/uploads/?limit=50")

            if response.status_code == 200:
                data = response.json()
                uploads = data.get("uploads", [])

                # Filter only completed uploads
                completed = [u for u in uploads if u.get("processing_status") == "completed"]

                if not completed:
                    return [], {}

                # Create dropdown choices: display name -> upload_id mapping
                choices = []
                pdf_mapping = {}

                for upload in completed:
                    upload_id = upload.get("upload_id", "")
                    filename = upload.get("filename", "Unknown")
                    title = upload.get("title", "No title")

                    # Use title if available, otherwise filename
                    display_name = f"{title} ({filename})" if title and title != "No title" else filename
                    choices.append(display_name)
                    pdf_mapping[display_name] = upload_id

                return choices, pdf_mapping
            else:
                return [], {}

    except Exception as e:
        logger.error(f"Error fetching completed PDFs: {e}")
        return [], {}


async def stream_pdf_response(
    selected_pdf: Optional[str], query: str, top_k: int = 3, use_hybrid: bool = True, model: str = DEFAULT_MODEL
) -> Iterator[str]:
    """Stream response from the RAG API for a specific PDF"""
    if not query.strip():
        yield "Please enter a question."
        return

    if not selected_pdf:
        yield "⚠️ Please select a PDF first using the dropdown above."
        return

    # Get the upload_id from the selected PDF (passed as state)
    try:
        # The selected_pdf should be the upload_id directly
        source_ids = [selected_pdf]
    except Exception as e:
        yield f"Error: Could not identify selected PDF - {e}"
        return

    # Prepare request payload with source_ids
    payload = {"query": query, "top_k": top_k, "use_hybrid": use_hybrid, "model": model, "source_ids": source_ids}

    try:
        url = f"{API_BASE_URL}/stream"
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload, headers={"Accept": "text/plain"}) as response:
                if response.status_code != 200:
                    yield f"Error: API returned status {response.status_code}"
                    return

                current_answer = ""
                sources = []
                chunks_used = 0
                search_mode = ""

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        try:
                            data = json.loads(data_str)

                            # Handle error
                            if "error" in data:
                                yield f"Error: {data['error']}"
                                return

                            # Handle metadata
                            if "sources" in data:
                                sources = data["sources"]
                                chunks_used = data.get("chunks_used", 0)
                                search_mode = data.get("search_mode", "unknown")
                                continue

                            # Handle streaming chunks
                            if "chunk" in data:
                                current_answer += data["chunk"]
                                # Format response with sources if we have them
                                formatted_response = current_answer
                                if chunks_used:
                                    formatted_response += f"\n\n**Search Info:**\n"
                                    formatted_response += f"- Mode: {search_mode}\n"
                                    formatted_response += f"- Chunks used: {chunks_used}\n"

                                yield formatted_response

                            # Handle completion
                            if data.get("done", False):
                                final_answer = data.get("answer", current_answer)
                                if final_answer != current_answer:
                                    current_answer = final_answer

                                # Final formatted response
                                formatted_response = current_answer
                                if chunks_used:
                                    formatted_response += f"\n\n**Search Info:**\n"
                                    formatted_response += f"- Mode: {search_mode}\n"
                                    formatted_response += f"- Chunks used: {chunks_used}\n"

                                yield formatted_response
                                break

                        except json.JSONDecodeError:
                            continue  # Skip malformed JSON lines

    except httpx.RequestError as e:
        yield f"Connection error: {str(e)}\nMake sure the API server is running at {API_BASE_URL}"
    except Exception as e:
        yield f"Unexpected error: {str(e)}"


async def stream_response(
    query: str, top_k: int = 3, use_hybrid: bool = True, model: str = DEFAULT_MODEL, categories: str = ""
) -> Iterator[str]:
    """Stream response from the RAG API"""
    if not query.strip():
        yield "Please enter a question."
        return

    # Parse categories
    category_list = [cat.strip() for cat in categories.split(",") if cat.strip()] if categories else None

    # Prepare request payload
    payload = {"query": query, "top_k": top_k, "use_hybrid": use_hybrid, "model": model, "categories": category_list}

    try:
        url = f"{API_BASE_URL}/stream"
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload, headers={"Accept": "text/plain"}) as response:
                if response.status_code != 200:
                    yield f"Error: API returned status {response.status_code}"
                    return

                current_answer = ""
                sources = []
                chunks_used = 0
                search_mode = ""

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        try:
                            data = json.loads(data_str)

                            # Handle error
                            if "error" in data:
                                yield f"Error: {data['error']}"
                                return

                            # Handle metadata
                            if "sources" in data:
                                sources = data["sources"]
                                chunks_used = data.get("chunks_used", 0)
                                search_mode = data.get("search_mode", "unknown")
                                continue

                            # Handle streaming chunks
                            if "chunk" in data:
                                current_answer += data["chunk"]
                                # Format response with sources if we have them
                                formatted_response = current_answer
                                if sources or chunks_used:
                                    formatted_response += f"\n\n**Search Info:**\n"
                                    formatted_response += f"- Mode: {search_mode}\n"
                                    formatted_response += f"- Chunks used: {chunks_used}\n"
                                    if sources:
                                        formatted_response += f"- Sources: {len(sources)} papers\n"
                                        for i, source in enumerate(sources[:3], 1):  # Show first 3 sources
                                            formatted_response += f"  {i}. [{source.split('/')[-1]}]({source})\n"
                                        if len(sources) > 3:
                                            formatted_response += f"  ... and {len(sources) - 3} more\n"

                                yield formatted_response

                            # Handle completion
                            if data.get("done", False):
                                final_answer = data.get("answer", current_answer)
                                if final_answer != current_answer:
                                    current_answer = final_answer

                                # Final formatted response
                                formatted_response = current_answer
                                if sources or chunks_used:
                                    formatted_response += f"\n\n**Search Info:**\n"
                                    formatted_response += f"- Mode: {search_mode}\n"
                                    formatted_response += f"- Chunks used: {chunks_used}\n"
                                    if sources:
                                        formatted_response += f"- Sources: {len(sources)} papers\n"
                                        for i, source in enumerate(sources[:3], 1):
                                            formatted_response += f"  {i}. [{source.split('/')[-1]}]({source})\n"
                                        if len(sources) > 3:
                                            formatted_response += f"  ... and {len(sources) - 3} more\n"

                                yield formatted_response
                                break

                        except json.JSONDecodeError:
                            continue  # Skip malformed JSON lines

    except httpx.RequestError as e:
        yield f"Connection error: {str(e)}\nMake sure the API server is running at {API_BASE_URL}"
    except Exception as e:
        yield f"Unexpected error: {str(e)}"


def create_gradio_interface():
    """Create and configure the Gradio interface"""

    with gr.Blocks(
        title="arXiv Paper Curator - RAG Chat",
        theme=gr.themes.Soft(),
    ) as interface:
        gr.Markdown(
            """
            # 🔬 arXiv Paper Curator - RAG Chat
            
            Ask questions about machine learning and AI research papers from arXiv, or upload your own PDFs!
            The system will search through indexed papers and provide answers with sources.
            """
        )

        with gr.Tabs():
            # Chat Tab
            with gr.Tab("💬 Chat"):
                with gr.Row():
                    with gr.Column(scale=3):
                        query_input = gr.Textbox(
                            label="Your Question", placeholder="What are transformers in machine learning?", lines=2, max_lines=5
                        )

                    with gr.Column(scale=1):
                        submit_btn = gr.Button("Ask Question", variant="primary", size="lg")

                with gr.Row():
                    with gr.Column():
                        with gr.Accordion("Advanced Options", open=False):
                            top_k = gr.Slider(
                                minimum=1,
                                maximum=10,
                                value=3,
                                step=1,
                                label="Number of chunks to retrieve",
                                info="More chunks = more context but slower generation",
                            )

                            use_hybrid = gr.Checkbox(
                                value=True,
                                label="Use hybrid search (BM25 + vector embeddings)",
                                info="Usually better results than keyword-only search",
                            )

                            model_choice = gr.Dropdown(
                                choices=["llama3.2:1b", "llama3.2:3b", "llama3.1:8b", "qwen2.5:7b"],
                                value=DEFAULT_MODEL,
                                label="LLM Model",
                                info="Larger models may give better answers but are slower",
                            )

                            categories = gr.Textbox(
                                label="arXiv Categories (optional)",
                                placeholder="cs.AI, cs.LG, cs.CL",
                                info="Comma-separated. Leave empty for all categories",
                            )

                response_output = gr.Markdown(
                    label="Answer", value="Ask a question to get started!", height=400, elem_classes=["response-markdown"]
                )

                # Examples
                gr.Examples(
                    examples=[
                        ["What are transformers in machine learning?", 3, True, "llama3.2:1b", "cs.AI, cs.LG"],
                        ["How do convolutional neural networks work?", 5, True, "llama3.2:1b", "cs.CV, cs.LG"],
                        ["What is attention mechanism in deep learning?", 4, False, "llama3.2:1b", "cs.AI"],
                        ["Explain reinforcement learning algorithms", 3, True, "llama3.2:1b", "cs.LG, cs.AI"],
                        ["What are the latest developments in NLP?", 5, True, "llama3.2:1b", "cs.CL"],
                    ],
                    inputs=[query_input, top_k, use_hybrid, model_choice, categories],
                )

                # Handle submission
                submit_btn.click(
                    fn=stream_response,
                    inputs=[query_input, top_k, use_hybrid, model_choice, categories],
                    outputs=[response_output],
                    show_progress=True,
                )

                # Handle Enter key
                query_input.submit(
                    fn=stream_response,
                    inputs=[query_input, top_k, use_hybrid, model_choice, categories],
                    outputs=[response_output],
                    show_progress=True,
                )

            # Chat with PDF Tab
            with gr.Tab("📄 Chat with PDF"):
                gr.Markdown(
                    """
                    ### Chat with a Specific PDF
                    
                    Select one of your uploaded PDFs and ask questions about it specifically.
                    Only content from the selected document will be used to answer your questions.
                    """
                )

                # PDF Selection
                with gr.Row():
                    with gr.Column():
                        pdf_selector = gr.Dropdown(
                            label="Select a PDF",
                            choices=[],
                            value=None,
                            interactive=True,
                            info="Choose a PDF from your completed uploads",
                        )

                        # Hidden state to store upload_id mapping
                        pdf_mapping_state = gr.State(value={})
                        selected_upload_id = gr.State(value=None)

                        refresh_pdfs_btn = gr.Button("🔄 Refresh PDF List", variant="secondary", size="sm")

                        selected_pdf_info = gr.Markdown(value="*No PDF selected*")

                with gr.Row():
                    with gr.Column(scale=3):
                        pdf_query_input = gr.Textbox(
                            label="Your Question", placeholder="Ask a question about this PDF...", lines=2, max_lines=5
                        )

                    with gr.Column(scale=1):
                        pdf_submit_btn = gr.Button("Ask Question", variant="primary", size="lg")

                with gr.Row():
                    with gr.Column():
                        with gr.Accordion("Advanced Options", open=False):
                            pdf_top_k = gr.Slider(
                                minimum=1,
                                maximum=10,
                                value=3,
                                step=1,
                                label="Number of chunks to retrieve",
                                info="More chunks = more context but slower generation",
                            )

                            pdf_use_hybrid = gr.Checkbox(
                                value=True,
                                label="Use hybrid search (BM25 + vector embeddings)",
                                info="Usually better results than keyword-only search",
                            )

                            pdf_model_choice = gr.Dropdown(
                                choices=["llama3.2:1b", "llama3.2:3b", "llama3.1:8b", "qwen2.5:7b"],
                                value=DEFAULT_MODEL,
                                label="LLM Model",
                                info="Larger models may give better answers but are slower",
                            )

                pdf_response_output = gr.Markdown(
                    label="Answer",
                    value="Select a PDF above and ask a question to get started!",
                    height=400,
                    elem_classes=["response-markdown"],
                )

                # Function to refresh PDF list
                async def refresh_pdf_dropdown():
                    choices, mapping = await get_completed_pdfs()
                    if not choices:
                        return (
                            gr.Dropdown(choices=[], value=None),
                            mapping,
                            "*No completed PDFs found. Upload and process a PDF first.*",
                        )
                    return (
                        gr.Dropdown(choices=choices, value=None),
                        mapping,
                        f"*Found {len(choices)} PDF(s). Select one to start chatting.*",
                    )

                # Function to update selected PDF info
                def update_pdf_selection(selected_display_name, pdf_mapping):
                    if not selected_display_name or not pdf_mapping:
                        return None, "*No PDF selected*"

                    upload_id = pdf_mapping.get(selected_display_name)
                    if upload_id:
                        return upload_id, f"**Selected:** {selected_display_name}\n\n*Upload ID: `{upload_id}`*"
                    return None, "*No PDF selected*"

                # Handle refresh button
                refresh_pdfs_btn.click(
                    fn=refresh_pdf_dropdown,
                    inputs=[],
                    outputs=[pdf_selector, pdf_mapping_state, selected_pdf_info],
                    show_progress=True,
                )

                # Handle PDF selection
                pdf_selector.change(
                    fn=update_pdf_selection,
                    inputs=[pdf_selector, pdf_mapping_state],
                    outputs=[selected_upload_id, selected_pdf_info],
                )

                # Handle submission
                pdf_submit_btn.click(
                    fn=stream_pdf_response,
                    inputs=[selected_upload_id, pdf_query_input, pdf_top_k, pdf_use_hybrid, pdf_model_choice],
                    outputs=[pdf_response_output],
                    show_progress=True,
                )

                # Handle Enter key
                pdf_query_input.submit(
                    fn=stream_pdf_response,
                    inputs=[selected_upload_id, pdf_query_input, pdf_top_k, pdf_use_hybrid, pdf_model_choice],
                    outputs=[pdf_response_output],
                    show_progress=True,
                )

            # Upload Tab
            with gr.Tab("📤 Upload PDF"):
                gr.Markdown(
                    """
                    ### Upload Your Own PDFs
                    
                    Upload PDF documents to add them to the RAG system. Your PDFs will be:
                    1. Parsed and analyzed
                    2. Chunked into searchable segments
                    3. Embedded and indexed for retrieval
                    4. Available for questions in the Chat tab
                    
                    **Supported**: PDF files up to 20MB
                    """
                )

                with gr.Row():
                    with gr.Column():
                        pdf_upload = gr.File(
                            label="Choose PDF File",
                            file_types=[".pdf"],
                            type="filepath",
                        )
                        upload_btn = gr.Button("Upload PDF", variant="primary", size="lg")
                        upload_status = gr.Markdown(value="Select a PDF file and click Upload")

                gr.Markdown("---")

                # Process uploaded PDF
                gr.Markdown("### Process Uploaded PDF")
                with gr.Row():
                    with gr.Column():
                        upload_id_input = gr.Textbox(
                            label="Upload ID",
                            placeholder="Paste your upload ID here",
                            info="Get this from the upload response above",
                        )
                        with gr.Row():
                            process_btn = gr.Button("Process PDF", variant="primary")
                            status_check_btn = gr.Button("Check Status", variant="secondary")
                        process_status = gr.Markdown(value="Enter an upload ID and click Process or Check Status")

                # Handle upload
                upload_btn.click(
                    fn=upload_pdf_handler,
                    inputs=[pdf_upload],
                    outputs=[upload_status],
                    show_progress=True,
                )

                # Handle process
                process_btn.click(
                    fn=process_upload_handler,
                    inputs=[upload_id_input],
                    outputs=[process_status],
                    show_progress=True,
                )

                # Handle status check
                status_check_btn.click(
                    fn=check_upload_status,
                    inputs=[upload_id_input],
                    outputs=[process_status],
                    show_progress=True,
                )

            # My Uploads Tab
            with gr.Tab("📚 My Uploads"):
                gr.Markdown("### Your Uploaded PDFs")

                refresh_btn = gr.Button("🔄 Refresh List", variant="secondary")
                uploads_list = gr.Markdown(value="Click Refresh to load your uploads")

                # Handle refresh
                refresh_btn.click(
                    fn=list_uploads_handler,
                    inputs=[],
                    outputs=[uploads_list],
                    show_progress=True,
                )

        gr.Markdown(
            """
            ---
            
            **Note**: Make sure the RAG API server is running at `http://localhost:8000` before using this interface.
            
            **Categories**: cs.AI (Artificial Intelligence), cs.LG (Machine Learning), cs.CL (Computational Linguistics), 
            cs.CV (Computer Vision), cs.NE (Neural Networks), stat.ML (Statistics - Machine Learning)
            """
        )

    return interface


def main():
    """Main entry point for the Gradio app"""
    print("🚀 Starting arXiv Paper Curator Gradio Interface...")
    print(f"📡 API Base URL: {API_BASE_URL}")

    interface = create_gradio_interface()

    # Launch the interface
    interface.launch(
        server_name="0.0.0.0",
        server_port=7861,  # Changed to avoid port conflict
        share=False,
        show_error=True,
        quiet=False,
    )


if __name__ == "__main__":
    main()
