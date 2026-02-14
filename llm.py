from google import genai
from PIL import Image
import base64
import io
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please check your .env file.")

client = genai.Client(api_key=api_key)

class LLMS:
    def __init__(self, nlp_model_name="gemini-2.5-flash", vision_model_name="gemini-2.5-flash"):
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
    
    def validate_ux_flow(self, images, total_count):
            """
            Validate UX flow across multiple screens using Gemini Vision.

            Args:
                images: List of dicts with 'index' and 'image' (base64) fields
                total_count: Total number of screens in the flow

            Returns:
                Structured JSON validation report
            """
            try:
                print(f"[DEBUG] Starting UX flow validation for {total_count} images")

                # Process all images
                processed_images = []
                for idx, img_data in enumerate(images):
                    try:
                        print(f"[DEBUG] Processing image {idx} with index {img_data.get('index')}")
                        img = self._process_image(img_data["image"])
                        processed_images.append({
                            "index": img_data["index"],
                            "image": img
                        })
                        print(f"[DEBUG] Successfully processed image {idx}")
                    except Exception as e:
                        print(f"[ERROR] Failed to process image {idx}: {str(e)}")
                        raise Exception(f"Image processing failed for image {idx}: {str(e)}")

                # Build the UX validation prompt
                print("[DEBUG] Building UX validation prompt")
                prompt = self._build_ux_validation_prompt(total_count)

                # Prepare content for Gemini (prompt + all images in order)
                content = [prompt]
                for img_data in processed_images:
                    content.append(img_data["image"])

                print(f"[DEBUG] Calling Gemini Vision API with {len(content)} items (1 prompt + {len(processed_images)} images)")

                # Call Gemini Vision with all images
                try:
                    response = client.models.generate_content(
                        model=self.vision_model,
                        contents=content
                    )
                    print("[DEBUG] Successfully received response from Gemini Vision API")
                    print(f"[DEBUG] Response text length: {len(response.text)} characters")
                except Exception as e:
                    print(f"[ERROR] Gemini API call failed: {str(e)}")
                    raise Exception(f"Gemini Vision API error: {str(e)}")

                # Parse and structure the response
                print("[DEBUG] Parsing validation response")
                validation_report = self._parse_ux_validation_response(response.text)
                print("[DEBUG] Validation report parsed successfully")
                print(f"[DEBUG] Validation report: {json.dumps(validation_report, indent=2)}")

                return validation_report

            except Exception as e:
                print(f"[ERROR] validate_ux_flow failed: {str(e)}")
                import traceback
                print(f"[ERROR] Traceback: {traceback.format_exc()}")
                raise

    
    def _build_ux_validation_prompt(self, total_count):
        """Build the prompt for UX flow validation."""
        prompt = f"""You are a UX/UI expert analyzing a user flow across {total_count} screens. The images are provided in sequential order (screen 1, screen 2, ..., screen {total_count}).

**Task**: Validate the UX flow from start to end and provide comprehensive analysis.

**Analysis Required**:
1. **Flow Order Validation**: Is the sequence logical and follows standard UX patterns?
2. **Field Presence**: Are all necessary fields present at each step?
3. **Navigation Consistency**: Are navigation elements (buttons, links, back actions) consistent?
4. **Visual Consistency**: Do screens maintain consistent design language (colors, fonts, spacing)?
5. **User Journey**: Does the flow make sense from a user perspective?
6. **Missing Steps**: Are there any obvious missing screens or steps?
7. **Error States**: Are error states or validation messages visible where needed?
8. **Accessibility**: Are there any obvious accessibility concerns?

**Output Format** (strict JSON):
{{
  "overall_assessment": {{
    "is_flow_correct": <boolean>,
    "flow_quality_score": <number 0-100>,
    "severity": "excellent|good|fair|poor|critical",
    "summary": "<brief overall assessment>"
  }},
  "flow_analysis": {{
    "logical_order": {{
      "is_correct": <boolean>,
      "description": "<explanation of flow order>",
      "issues": ["<issue 1>", "<issue 2>"]
    }},
    "screen_transitions": [
      {{
        "from_screen": <number>,
        "to_screen": <number>,
        "transition_type": "<type of transition>",
        "is_smooth": <boolean>,
        "issues": ["<issue if any>"]
      }}
    ]
  }},
  "screen_by_screen_analysis": [
    {{
      "screen_index": <number>,
      "screen_title": "<identified screen name/purpose>",
      "fields_present": ["<field 1>", "<field 2>"],
      "missing_fields": ["<expected field that's missing>"],
      "navigation_elements": ["<button/link 1>", "<button/link 2>"],
      "issues": [
        {{
          "type": "missing_field|layout_issue|navigation_issue|accessibility_issue",
          "severity": "critical|high|medium|low",
          "description": "<detailed description>"
        }}
      ],
      "recommendations": ["<recommendation 1>", "<recommendation 2>"]
    }}
  ],
  "consistency_check": {{
    "visual_consistency": {{
      "is_consistent": <boolean>,
      "issues": ["<inconsistency 1>", "<inconsistency 2>"]
    }},
    "navigation_consistency": {{
      "is_consistent": <boolean>,
      "issues": ["<inconsistency 1>", "<inconsistency 2>"]
    }},
    "branding_consistency": {{
      "is_consistent": <boolean>,
      "issues": ["<inconsistency 1>", "<inconsistency 2>"]
    }}
  }},
  "missing_steps": [
    {{
      "after_screen": <number>,
      "suggested_screen": "<description of missing screen>",
      "reason": "<why this screen is needed>"
    }}
  ],
  "recommendations": [
    {{
      "priority": "critical|high|medium|low",
      "category": "flow|design|accessibility|functionality",
      "description": "<actionable recommendation>",
      "affected_screens": [<screen indices>]
    }}
  ],
  "user_journey_assessment": {{
    "clarity": <number 0-100>,
    "ease_of_use": <number 0-100>,
    "completion_likelihood": <number 0-100>,
    "pain_points": ["<pain point 1>", "<pain point 2>"],
    "strengths": ["<strength 1>", "<strength 2>"]
  }}
}}

Analyze all {total_count} screens carefully in the order provided and give a comprehensive UX validation report in the exact JSON format specified above."""
        
        return prompt
    
    def _parse_ux_validation_response(self, response_text):
        """Parse Gemini Vision response for UX validation."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            validation_report = json.loads(response_text)
            
            # Ensure required fields exist
            if "overall_assessment" not in validation_report:
                validation_report["overall_assessment"] = {
                    "is_flow_correct": False,
                    "flow_quality_score": 0,
                    "severity": "unknown",
                    "summary": "Unable to assess flow"
                }
            
            if "flow_analysis" not in validation_report:
                validation_report["flow_analysis"] = {
                    "logical_order": {"is_correct": False, "description": "", "issues": []},
                    "screen_transitions": []
                }
            
            if "screen_by_screen_analysis" not in validation_report:
                validation_report["screen_by_screen_analysis"] = []
            
            if "consistency_check" not in validation_report:
                validation_report["consistency_check"] = {
                    "visual_consistency": {"is_consistent": True, "issues": []},
                    "navigation_consistency": {"is_consistent": True, "issues": []},
                    "branding_consistency": {"is_consistent": True, "issues": []}
                }
            
            if "missing_steps" not in validation_report:
                validation_report["missing_steps"] = []
            
            if "recommendations" not in validation_report:
                validation_report["recommendations"] = []
            
            if "user_journey_assessment" not in validation_report:
                validation_report["user_journey_assessment"] = {
                    "clarity": 0,
                    "ease_of_use": 0,
                    "completion_likelihood": 0,
                    "pain_points": [],
                    "strengths": []
                }
            
            return validation_report
            
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "overall_assessment": {
                    "is_flow_correct": False,
                    "flow_quality_score": 0,
                    "severity": "error",
                    "summary": "Failed to parse validation response"
                },
                "raw_response": response_text,
                "flow_analysis": {
                    "logical_order": {"is_correct": False, "description": "Parse error", "issues": []},
                    "screen_transitions": []
                },
                "screen_by_screen_analysis": [],
                "consistency_check": {
                    "visual_consistency": {"is_consistent": False, "issues": ["Parse error"]},
                    "navigation_consistency": {"is_consistent": False, "issues": ["Parse error"]},
                    "branding_consistency": {"is_consistent": False, "issues": ["Parse error"]}
                },
                "missing_steps": [],
                "recommendations": [],
                "user_journey_assessment": {
                    "clarity": 0,
                    "ease_of_use": 0,
                    "completion_likelihood": 0,
                    "pain_points": ["Unable to analyze due to parse error"],
                    "strengths": []
                }
            }
    
    def nlp(self, prompt):
        """General NLP query using Gemini."""
        response = client.models.generate_content(
            model=self.nlp_model,
            contents=[prompt]
        )
        return response.text
    