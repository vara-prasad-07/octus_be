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
from models import PlanningRequest, PlanningResponse, InsightsRequest, InsightsResponse
from planning_service import PlanningService

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

# Initialize Planning service
planning_service = PlanningService()

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

@app.post("/validateux")
async def validate_ux(request: dict):
    """
    UX Flow Validation endpoint.
    
    Validates the UX flow from starting UI page to end based on user-provided images.
    Uses Gemini Vision to analyze the flow order, field presence, and UX consistency.
    
    Expected JSON format:
    {
        "totalCount": 3,
        "images": [
            {"index": 0, "image": "data:image/png;base64,..."},
            {"index": 1, "image": "data:image/png;base64,..."},
            {"index": 2, "image": "data:image/png;base64,..."}
        ]
    }
    
    Returns structured validation report with flow analysis.
    """
    try:
        print("[DEBUG] Received request to /validateux endpoint")
        print(f"[DEBUG] Request data: {json.dumps(request, default=str)[:500]}...")  # Print first 500 chars
        
        # Validate request structure
        if "images" not in request or "totalCount" not in request:
            raise HTTPException(
                status_code=400,
                detail="Invalid request format. Expected 'images' array and 'totalCount' field."
            )
        
        images = request.get("images", [])
        total_count = request.get("totalCount", 0)
        user_prompt = request.get("user_prompt", "")
        
        # Validate image count
        if len(images) != total_count:
            raise HTTPException(
                status_code=400,
                detail=f"Image count mismatch. Expected {total_count}, got {len(images)}"
            )
        
        if total_count == 0:
            raise HTTPException(
                status_code=400,
                detail="No images provided for UX validation"
            )
        
        # Sort images by index to ensure correct order
        sorted_images = sorted(images, key=lambda x: x.get("index", 0))
        
        # Validate each image has required fields
        for img in sorted_images:
            if "image" not in img or "index" not in img:
                raise HTTPException(
                    status_code=400,
                    detail="Each image must have 'image' (base64) and 'index' fields"
                )
        
        # Perform UX flow validation using Gemini Vision
        validation_report = llm_service.validate_ux_flow(sorted_images, total_count, user_prompt)
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "UX flow validation completed",
                "validation_report": validation_report,
                "metadata": {
                    "total_screens": total_count,
                    "screens_analyzed": len(sorted_images)
                }
            },
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] validate_ux endpoint failed: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing UX validation: {str(e)}"
        )


@app.post("/visualregressions")
async def visual_regressions(request: dict):
    """
    Visual Regression Detection endpoint.
    
    Analyzes a single UI screenshot to detect visual regressions, broken components,
    overlapping elements, and other UI issues.
    
    Expected JSON format:
    {
        "image": "data:image/png;base64,...",
        "context": "Optional description of what this screen should look like"
    }
    
    Returns structured inspection report with detected issues.
    """
    try:
        print("[DEBUG] Received request to /visualregressions endpoint")
        print(f"[DEBUG] Request keys: {list(request.keys())}")
        
        # Validate request structure
        if "image" not in request:
            raise HTTPException(
                status_code=400,
                detail="Invalid request format. Expected 'image' field with base64 encoded image."
            )
        
        image_data = request.get("image")
        context = request.get("context", "")
        
        if not image_data:
            raise HTTPException(
                status_code=400,
                detail="Image data is empty"
            )
        
        print("[DEBUG] Calling visual regression analysis")
        
        # Perform visual regression analysis using Gemini Vision
        inspection_report = llm_service.analyze_visual_regressions(image_data, context)
        
        print("[DEBUG] Visual regression analysis completed successfully")
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Visual regression analysis completed",
                "inspection_report": inspection_report,
                "metadata": {
                    "has_context": bool(context),
                    "analysis_timestamp": json.dumps({"timestamp": "now"})
                }
            },
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] visual_regressions endpoint failed: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing visual regression analysis: {str(e)}"
        )


@app.post('/planning/analyze', response_model=PlanningResponse)
async def analyze_planning(request: PlanningRequest):
    """
    AI-Powered Planning Analysis endpoint.
    
    Analyzes project tasks and provides:
    - Risk scoring per task
    - Velocity calculations
    - Workload analysis
    - Dependency risk propagation
    - Predicted release delays
    - AI-generated recommendations
    - Executive health summary
    
    Returns comprehensive planning analysis.
    """
    try:
        # Validate input
        if not request.tasks:
            raise HTTPException(
                status_code=400,
                detail="No tasks provided for analysis"
            )
        
        print(f"Received analysis request for project: {request.projectId}")
        print(f"Number of tasks: {len(request.tasks)}")
        print(f"Team capacity members: {len(request.team_capacity)}")
        
        # Perform planning analysis
        analysis_result = planning_service.analyze_planning(request)
        
        print(f"Analysis complete. Overall risk: {analysis_result.overall_risk_score}")
        
        return analysis_result

        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in planning analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error performing planning analysis: {str(e)}"
        )

@app.post('/insights')
async def generate_insights(request: InsightsRequest):
    """
    AI-Powered Quality Insights endpoint.
    
    Analyzes project quality data and provides:
    - Defect trends across builds
    - Quality hotspots by module
    - Release readiness score (0-100)
    - Release decision (RELEASE/CAUTION/BLOCK)
    - Actionable recommendations
    
    Expected JSON format:
    {
        "testGenerationHistory": {...},
        "uiValidations": {...},
        "uxValidations": {...}
    }
    
    Returns comprehensive quality insights.
    """
    try:
        print("[DEBUG] Received insights request")
        print(f"[DEBUG] Test generation history keys: {list(request.testGenerationHistory.keys())}")
        print(f"[DEBUG] UI validations keys: {list(request.uiValidations.keys())}")
        print(f"[DEBUG] UX validations keys: {list(request.uxValidations.keys())}")
        
        # Generate insights using LLM
        insights_report = llm_service.generate_insights(
            test_generation_history=request.testGenerationHistory,
            ui_validations=request.uiValidations,
            ux_validations=request.uxValidations
        )
        
        print(f"[DEBUG] Insights generated successfully")
        print(f"[DEBUG] Release decision: {insights_report.get('release_readiness', {}).get('decision', 'UNKNOWN')}")
        print(f"[DEBUG] Release score: {insights_report.get('release_readiness', {}).get('score', 0)}")
        
        return JSONResponse(
            content={
                "status": "success",
                "message": "Quality insights generated successfully",
                "insights": insights_report
            },
            status_code=200
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] insights endpoint failed: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating insights: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
