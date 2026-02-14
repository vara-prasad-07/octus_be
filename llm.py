from google import genai
from PIL import Image
import base64
import io
import json
import os

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
api_key = os.getenv("GEMINI_API_KEY","")
client = genai.Client(api_key=api_key)

class LLMS:
    def __init__(self, nlp_model_name="gemini-3-flash-preview", vision_model_name="gemini-3-flash-preview"):
        self.nlp_model = nlp_model_name
        self.vision_model = vision_model_name
        
    def ui_comparison(self, baseline_image, comparison_image, element_labels=None, tolerance=5, test_description=""):
        """
        Compare two UI screenshots using Gemini Vision.
        
        Args:
            baseline_image: PIL Image or base64 string of baseline screenshot (v1)
            comparison_image: PIL Image or base64 string of comparison screenshot (v2)
            element_labels: Optional dict with element labels and coordinates
            tolerance: Acceptable pixel-shift tolerance percentage (default: 5%)
            test_description: Optional description of the test flow
            
        Returns:
            Structured JSON diff report
        """
        
        # Convert base64 to PIL Image if needed
        baseline_img = self._process_image(baseline_image)
        comparison_img = self._process_image(comparison_image)
        
        # Build the prompt for Gemini Vision
        prompt = self._build_comparison_prompt(element_labels, tolerance, test_description)
        
        # Call Gemini Vision with both images
        response = client.models.generate_content(
            model=self.vision_model,
            contents=[prompt, baseline_img, comparison_img]
        )
        
        # Parse and structure the response
        diff_report = self._parse_vision_response(response.text, tolerance)
        
        return diff_report
    
    def _process_image(self, image):
        """Convert base64 string to PIL Image if needed."""
        if isinstance(image, str):
            # Assume it's base64 encoded
            if image.startswith('data:image'):
                image = image.split(',')[1]
            image_data = base64.b64decode(image)
            return Image.open(io.BytesIO(image_data))
        return image
    
    def _build_comparison_prompt(self, element_labels, tolerance, test_description):
        """Build the multimodal prompt for UI comparison."""
        prompt = f"""You are a UI/UX QA expert performing visual regression testing. Compare these two UI screenshots (baseline v1 vs comparison v2).

**Task**: Detect visual regressions, missing UI elements, layout shifts, broken flows, and color/contrast anomalies.

**Test Description**: {test_description if test_description else "General UI comparison"}

**Tolerance**: {tolerance}% pixel-shift tolerance for layout changes.

**Element Labels**: {json.dumps(element_labels) if element_labels else "No specific elements labeled"}

**Analysis Required**:
1. Identify missing or new UI elements
2. Detect layout shifts (position changes beyond tolerance)
3. Find color/contrast differences
4. Spot broken UI flows or visual bugs
5. Note any text changes or truncation
6. Identify spacing/padding differences

**Output Format** (strict JSON):
{{
  "summary": {{
    "total_changes": <number>,
    "severity": "critical|high|medium|low|none",
    "pass_fail_status": "pass|fail"
  }},
  "visual_regressions": [
    {{
      "element_name": "<element identifier>",
      "change_type": "missing|added|shifted|color_change|size_change|text_change",
      "severity": "critical|high|medium|low",
      "description": "<detailed description>",
      "baseline_state": "<description of v1>",
      "comparison_state": "<description of v2>",
      "coordinates": {{"x": <number>, "y": <number>, "width": <number>, "height": <number>}}
    }}
  ],
  "missing_elements": [
    {{
      "element_name": "<element that disappeared>",
      "expected_location": {{"x": <number>, "y": <number>}},
      "description": "<what was expected>"
    }}
  ],
  "layout_shifts": [
    {{
      "element_name": "<element that moved>",
      "shift_percentage": <number>,
      "baseline_position": {{"x": <number>, "y": <number>}},
      "comparison_position": {{"x": <number>, "y": <number>}},
      "exceeds_tolerance": <boolean>
    }}
  ],
  "color_contrast_issues": [
    {{
      "element_name": "<element with color change>",
      "issue_type": "color_change|contrast_issue",
      "description": "<description of the issue>"
    }}
  ]
}}

Analyze both images carefully and provide the structured JSON response."""
        
        return prompt
    
    def _parse_vision_response(self, response_text, tolerance):
        """Parse Gemini Vision response and ensure proper JSON structure."""
        try:
            # Try to extract JSON from response
            # Gemini might wrap JSON in markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            diff_report = json.loads(response_text)
            
            # Ensure all required fields exist
            if "summary" not in diff_report:
                diff_report["summary"] = {
                    "total_changes": 0,
                    "severity": "none",
                    "pass_fail_status": "pass"
                }
            
            if "visual_regressions" not in diff_report:
                diff_report["visual_regressions"] = []
            
            if "missing_elements" not in diff_report:
                diff_report["missing_elements"] = []
            
            if "layout_shifts" not in diff_report:
                diff_report["layout_shifts"] = []
            
            if "color_contrast_issues" not in diff_report:
                diff_report["color_contrast_issues"] = []
            
            return diff_report
            
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "summary": {
                    "total_changes": 0,
                    "severity": "unknown",
                    "pass_fail_status": "error",
                    "error": "Failed to parse Gemini Vision response"
                },
                "raw_response": response_text,
                "visual_regressions": [],
                "missing_elements": [],
                "layout_shifts": [],
                "color_contrast_issues": []
            }
    
    def nlp(self, prompt):
        """General NLP query using Gemini."""
        response = client.models.generate_content(
            model=self.nlp_model,
            contents=[prompt]
        )
        return response.text
    