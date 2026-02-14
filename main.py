from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import json 
import os
from PIL import Image
import io
from llm import LLMS

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
    expose_headers=["*"],  # Expose all headers
)

# Add GZip compression for JSON responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Initialize LLM service
llm_service = LLMS()

@app.get('/')
def start():
    return {"status": "server running", "message": "API is ready"}

@app.get('/health')
def health_check():
    return {"status": "healthy"}

@app.post('/uicomparison')
async def ui_comparison(
    baseline_image: UploadFile = File(..., description="Baseline screenshot (PNG/JPEG, v1)"),
    comparison_image: UploadFile = File(..., description="Comparison screenshot (PNG/JPEG, v2)"),
    element_labels: Optional[str] = Form(None, description="Optional element labels JSON"),
    tolerance: Optional[int] = Form(5, description="Acceptable pixel-shift tolerance %"),
    test_description: Optional[str] = Form("", description="Test flow description")
):
    """
    Vision-Based UI QA endpoint.
    
    Compares two UI screenshots using Gemini Vision to detect:
    - Visual regressions
    - Missing UI elements
    - Layout shifts
    - Broken flows
    - Color/contrast anomalies
    
    Returns structured JSON diff report.
    """
    try:
        # Validate file formats
        if not baseline_image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Baseline file must be an image (PNG/JPEG)")
        
        if not comparison_image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Comparison file must be an image (PNG/JPEG)")
        
        # Read and process images
        baseline_bytes = await baseline_image.read()
        comparison_bytes = await comparison_image.read()
        
        baseline_img = Image.open(io.BytesIO(baseline_bytes))
        comparison_img = Image.open(io.BytesIO(comparison_bytes))
        
        # Parse element labels if provided
        element_labels_dict = None
        if element_labels and element_labels.strip():
            try:
                element_labels_dict = json.loads(element_labels)
            except json.JSONDecodeError:
                # If it's not valid JSON, treat it as a simple string description
                element_labels_dict = {"description": element_labels}
        
        # Perform UI comparison using Gemini Vision
        diff_report = llm_service.ui_comparison(
            baseline_image=baseline_img,
            comparison_image=comparison_img,
            element_labels=element_labels_dict,
            tolerance=tolerance,
            test_description=test_description
        )
        
        # Return structured JSON diff report
        return JSONResponse(
            content={
                "status": "success",
                "message": "UI comparison completed",
                "diff_report": diff_report,
                "metadata": {
                    "baseline_size": f"{baseline_img.size[0]}x{baseline_img.size[1]}",
                    "comparison_size": f"{comparison_img.size[0]}x{comparison_img.size[1]}",
                    "tolerance": tolerance,
                    "test_description": test_description
                }
            },
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing UI comparison: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
