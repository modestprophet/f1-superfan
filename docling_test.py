import logging
from pathlib import Path
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import VlmPipelineOptions
from docling.datamodel.pipeline_options_vlm_model import ApiVlmOptions, ResponseFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.vlm_pipeline import VlmPipeline

def ollama_vlm_options(model: str, prompt: str):
    options = ApiVlmOptions(
        url="http://10.0.20.17:11434/v1/chat/completions",  # the default Ollama endpoint
        params=dict(
            model=model,
        ),
        prompt=prompt,
        timeout=90,
        scale=1.0,
        response_format=ResponseFormat.MARKDOWN,
    )
    return options

def main():
    logging.basicConfig(level=logging.INFO)

    data_folder = Path(__file__).parent / "images"
    input_doc_path = data_folder / "test_interval_2.png"

    pipeline_options = VlmPipelineOptions(
        enable_remote_services=True  # <-- this is required!
    )

    # Vision model with Ollama:
    pipeline_options.vlm_options = ollama_vlm_options(
        model="granite3.2-vision:2b",
        prompt="OCR the table on the left of the image to json.",
    )

    # Create the DocumentConverter and launch the conversion.
    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
                pipeline_cls=VlmPipeline,
            )
        }
    )
    result = doc_converter.convert(input_doc_path)
    print(result.document.export_to_markdown())

main()