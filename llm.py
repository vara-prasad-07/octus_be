from google import genai
from PIL import Image
import base64
import io
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get separate API keys for vision and NLP models
vision_api_key = os.getenv("VISION_GEMINI_API_KEY")
nlp_api_key = os.getenv("NLP_GEMINI_API_KEY")

# Initialize clients as None
vision_client = None
nlp_client = None

# Validate and create clients
if vision_api_key:
    vision_client = genai.Client(api_key=vision_api_key)
else:
    print("WARNING: VISION_GEMINI_API_KEY not found. Vision endpoints will not work.")

if nlp_api_key:
    nlp_client = genai.Client(api_key=nlp_api_key)
else:
    print("WARNING: NLP_GEMINI_API_KEY not found. NLP endpoints will not work.")

class LLMS:
    def __init__(self, nlp_model_name="gemini-3-pro", vision_model_name="gemini-2.5-flash"):
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
        
        # Check if vision client is available
        if not vision_client:
            raise ValueError("VISION_GEMINI_API_KEY not configured. Cannot perform UI comparison.")
        
        # Convert base64 to PIL Image if needed
        baseline_img = self._process_image(baseline_image)
        comparison_img = self._process_image(comparison_image)
        
        # Build the prompt for Gemini Vision
        prompt = self._build_comparison_prompt(element_labels, tolerance, test_description)
        
        # Call Gemini Vision with both images
        response = vision_client.models.generate_content(
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
    
    def validate_ux_flow(self, images, total_count, user_prompt=""):
            """
            Validate UX flow across multiple screens using Gemini Vision.

            Args:
                images: List of dicts with 'index' and 'image' (base64) fields
                total_count: Total number of screens in the flow
                user_prompt: Optional user-provided prompt to append to system prompt

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
                prompt = self._build_ux_validation_prompt(total_count, user_prompt)

                # Prepare content for Gemini (prompt + all images in order)
                content = [prompt]
                for img_data in processed_images:
                    content.append(img_data["image"])

                print(f"[DEBUG] Calling Gemini Vision API with {len(content)} items (1 prompt + {len(processed_images)} images)")

                # Call Gemini Vision with all images
                try:
                    response = vision_client.models.generate_content(
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

    
    def _build_ux_validation_prompt(self, total_count, user_prompt=""):
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
8. **Accessibility**: Are there any obvious accessibility concerns?"""

        # Append user prompt if provided
        if user_prompt and user_prompt.strip():
            prompt += f"\n\n**Additional User Instructions**:\n{user_prompt.strip()}"

        prompt += """

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
    
    def analyze_visual_regressions(self, image_data, context=""):
        """
        Analyze a single UI screenshot for visual regressions and UI issues.
        
        Args:
            image_data: Base64 encoded image string
            context: Optional description of what the screen should look like
            
        Returns:
            Structured JSON inspection report
        """
        try:
            print("[DEBUG] Starting visual regression analysis")
            
            # Process the image
            try:
                img = self._process_image(image_data)
                print(f"[DEBUG] Image processed successfully, size: {img.size}")
            except Exception as e:
                print(f"[ERROR] Failed to process image: {str(e)}")
                raise Exception(f"Image processing failed: {str(e)}")
            
            # Build the visual regression prompt
            print("[DEBUG] Building visual regression prompt")
            prompt = self._build_visual_regression_prompt(context)
            
            # Call Gemini Vision
            print("[DEBUG] Calling Gemini Vision API")
            try:
                response = vision_client.models.generate_content(
                    model=self.vision_model,
                    contents=[prompt, img]
                )
                print("[DEBUG] Successfully received response from Gemini Vision API")
                print(f"[DEBUG] Response text length: {len(response.text)} characters")
            except Exception as e:
                print(f"[ERROR] Gemini API call failed: {str(e)}")
                raise Exception(f"Gemini Vision API error: {str(e)}")
            
            # Parse and structure the response
            print("[DEBUG] Parsing visual regression response")
            inspection_report = self._parse_visual_regression_response(response.text)
            print("[DEBUG] Visual regression report parsed successfully")
            
            return inspection_report
            
        except Exception as e:
            print(f"[ERROR] analyze_visual_regressions failed: {str(e)}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            raise
    
    def _build_visual_regression_prompt(self, context):
        """Build the prompt for visual regression analysis."""
        prompt = f"""You are a UI/UX Quality Assurance expert performing a comprehensive visual inspection of a user interface screenshot.

**Context**: {context if context else "General UI inspection - no specific context provided"}

**Task**: Perform a thorough visual regression analysis to detect any UI issues, broken components, overlapping elements, and other visual problems.

**Inspection Checklist**:
1. **Broken Components**: Identify any UI elements that appear broken, cut off, or improperly rendered
2. **Overlapping Elements**: Detect components that overlap inappropriately or obscure other elements
3. **Layout Issues**: Find misaligned elements, incorrect spacing, or broken grid layouts
4. **Text Issues**: Identify truncated text, text overflow, unreadable text, or font rendering problems
5. **Image Issues**: Detect broken images, missing images, or improperly sized images
6. **Color & Contrast**: Find color contrast issues, accessibility problems, or inconsistent theming
7. **Responsive Issues**: Identify elements that appear to be incorrectly sized for the viewport
8. **Visual Hierarchy**: Detect problems with visual hierarchy or information architecture
9. **Interactive Elements**: Check if buttons, links, and interactive elements are properly visible and accessible
10. **Consistency**: Identify inconsistencies in design patterns, spacing, or styling

**Output Format** (strict JSON):
{{
  "overall_health": {{
    "status": "healthy|warning|critical",
    "health_score": <number 0-100>,
    "total_issues_found": <number>,
    "critical_issues": <number>,
    "summary": "<brief overall assessment>"
  }},
  "broken_components": [
    {{
      "component_type": "<type of component: button, input, card, etc>",
      "component_name": "<identifier or description>",
      "issue_description": "<detailed description of what's broken>",
      "severity": "critical|high|medium|low",
      "location": {{"x": <number>, "y": <number>, "width": <number>, "height": <number>}},
      "suggested_fix": "<actionable recommendation>"
    }}
  ],
  "overlapping_elements": [
    {{
      "element1": "<first overlapping element>",
      "element2": "<second overlapping element>",
      "overlap_description": "<description of the overlap>",
      "severity": "critical|high|medium|low",
      "location": {{"x": <number>, "y": <number>}},
      "suggested_fix": "<actionable recommendation>"
    }}
  ],
  "layout_issues": [
    {{
      "issue_type": "misalignment|spacing|grid_broken|positioning",
      "affected_elements": ["<element 1>", "<element 2>"],
      "description": "<detailed description>",
      "severity": "critical|high|medium|low",
      "location": {{"x": <number>, "y": <number>}},
      "suggested_fix": "<actionable recommendation>"
    }}
  ],
  "text_issues": [
    {{
      "issue_type": "truncated|overflow|unreadable|font_rendering",
      "text_content": "<the problematic text if visible>",
      "element": "<element containing the text>",
      "description": "<detailed description>",
      "severity": "critical|high|medium|low",
      "location": {{"x": <number>, "y": <number>}},
      "suggested_fix": "<actionable recommendation>"
    }}
  ],
  "image_issues": [
    {{
      "issue_type": "broken|missing|incorrect_size|distorted",
      "image_description": "<description of the image>",
      "description": "<detailed description of the issue>",
      "severity": "critical|high|medium|low",
      "location": {{"x": <number>, "y": <number>}},
      "suggested_fix": "<actionable recommendation>"
    }}
  ],
  "color_contrast_issues": [
    {{
      "element": "<affected element>",
      "issue_type": "low_contrast|accessibility|inconsistent_theme",
      "description": "<detailed description>",
      "severity": "critical|high|medium|low",
      "wcag_compliance": "<pass|fail|warning>",
      "suggested_fix": "<actionable recommendation>"
    }}
  ],
  "responsive_issues": [
    {{
      "element": "<affected element>",
      "issue_description": "<description of responsive issue>",
      "severity": "critical|high|medium|low",
      "suggested_fix": "<actionable recommendation>"
    }}
  ],
  "accessibility_concerns": [
    {{
      "concern_type": "contrast|focus_indicator|touch_target|screen_reader",
      "element": "<affected element>",
      "description": "<detailed description>",
      "severity": "critical|high|medium|low",
      "wcag_guideline": "<relevant WCAG guideline if applicable>",
      "suggested_fix": "<actionable recommendation>"
    }}
  ],
  "design_inconsistencies": [
    {{
      "inconsistency_type": "spacing|colors|fonts|patterns",
      "elements": ["<element 1>", "<element 2>"],
      "description": "<detailed description>",
      "severity": "critical|high|medium|low",
      "suggested_fix": "<actionable recommendation>"
    }}
  ],
  "positive_findings": [
    "<positive aspect 1>",
    "<positive aspect 2>"
  ],
  "recommendations": [
    {{
      "priority": "critical|high|medium|low",
      "category": "layout|design|accessibility|performance|consistency",
      "recommendation": "<detailed actionable recommendation>",
      "impact": "<expected impact of implementing this recommendation>"
    }}
  ]
}}

**Instructions**:
- Be thorough and precise in your analysis
- Provide specific locations (x, y coordinates) where possible
- Give actionable suggestions for fixing each issue
- If no issues are found in a category, return an empty array []
- Focus on actual visual problems, not subjective design preferences
- Prioritize issues that affect functionality and user experience

Analyze the UI screenshot carefully and provide the comprehensive inspection report in the exact JSON format specified above."""
        
        return prompt
    
    def _parse_visual_regression_response(self, response_text):
        """Parse Gemini Vision response for visual regression analysis."""
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
            
            inspection_report = json.loads(response_text)
            
            # Ensure all required fields exist with defaults
            if "overall_health" not in inspection_report:
                inspection_report["overall_health"] = {
                    "status": "unknown",
                    "health_score": 0,
                    "total_issues_found": 0,
                    "critical_issues": 0,
                    "summary": "Unable to assess"
                }
            
            if "broken_components" not in inspection_report:
                inspection_report["broken_components"] = []
            
            if "overlapping_elements" not in inspection_report:
                inspection_report["overlapping_elements"] = []
            
            if "layout_issues" not in inspection_report:
                inspection_report["layout_issues"] = []
            
            if "text_issues" not in inspection_report:
                inspection_report["text_issues"] = []
            
            if "image_issues" not in inspection_report:
                inspection_report["image_issues"] = []
            
            if "color_contrast_issues" not in inspection_report:
                inspection_report["color_contrast_issues"] = []
            
            if "responsive_issues" not in inspection_report:
                inspection_report["responsive_issues"] = []
            
            if "accessibility_concerns" not in inspection_report:
                inspection_report["accessibility_concerns"] = []
            
            if "design_inconsistencies" not in inspection_report:
                inspection_report["design_inconsistencies"] = []
            
            if "positive_findings" not in inspection_report:
                inspection_report["positive_findings"] = []
            
            if "recommendations" not in inspection_report:
                inspection_report["recommendations"] = []
            
            return inspection_report
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON parsing failed: {str(e)}")
            # Fallback if JSON parsing fails
            return {
                "overall_health": {
                    "status": "error",
                    "health_score": 0,
                    "total_issues_found": 0,
                    "critical_issues": 0,
                    "summary": "Failed to parse analysis response"
                },
                "error": "JSON parsing failed",
                "raw_response": response_text[:500],  # First 500 chars for debugging
                "broken_components": [],
                "overlapping_elements": [],
                "layout_issues": [],
                "text_issues": [],
                "image_issues": [],
                "color_contrast_issues": [],
                "responsive_issues": [],
                "accessibility_concerns": [],
                "design_inconsistencies": [],
                "positive_findings": [],
                "recommendations": []
            }
    
    def nlp(self, prompt):
        """General NLP query using Gemini."""
        response = nlp_client.models.generate_content(
            model=self.nlp_model,
            contents=[prompt]
        )
        return response.text
    
    def generate_insights(self, test_generation_history, ui_validations, ux_validations):
        """
        Generate quality insights from project data using Gemini.
        
        Args:
            test_generation_history: JSON data about test generation history
            ui_validations: JSON data about UI validation results
            ux_validations: JSON data about UX validation results
            
        Returns:
            Structured JSON insights report
        """
        try:
            print("[DEBUG] Starting insights generation")
            
            # Build the insights prompt
            prompt = self._build_insights_prompt(
                test_generation_history, 
                ui_validations, 
                ux_validations
            )
            
            print("[DEBUG] Calling Gemini API for insights")
            
            # Call Gemini NLP
            response = nlp_client.models.generate_content(
                model=self.nlp_model,
                contents=[prompt]
            )
            
            print("[DEBUG] Successfully received response from Gemini API")
            print(f"[DEBUG] Response text length: {len(response.text)} characters")
            
            # Parse and structure the response
            insights_report = self._parse_insights_response(response.text)
            print("[DEBUG] Insights report parsed successfully")
            
            return insights_report
            
        except Exception as e:
            print(f"[ERROR] generate_insights failed: {str(e)}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            raise
    
    def _build_insights_prompt(self, test_generation_history, ui_validations, ux_validations):
        """Build the prompt for insights generation."""
        prompt = f"""You are an AI quality analyst.

Using the provided test generation history, UI validation results, and UX validation results, generate a STRICT JSON response that includes:

1. Defect trends across builds (increasing, decreasing, or stable) with a short explanation.
2. Quality hotspots by module with severity levels (low, medium, high, critical).
3. A release readiness score between 0 and 100.
4. A release decision (RELEASE / CAUTION / BLOCK).
5. A short, human-readable recommendation.

Rules:
- Output ONLY valid JSON.
- Do NOT include explanations outside JSON.
- Use realistic engineering judgment.
- Assume unresolved critical defects heavily impact release readiness.

**Input Data**:

**Test Generation History**:
{json.dumps(test_generation_history, indent=2)}

**UI Validations**:
{json.dumps(ui_validations, indent=2)}

**UX Validations**:
{json.dumps(ux_validations, indent=2)}

**Required Output Format** (strict JSON):
{{
  "defect_trends": {{
    "trend": "increasing|decreasing|stable",
    "summary": "<short explanation of defect trends across builds>"
  }},
  "hotspots": [
    {{
      "module": "<module name>",
      "defect_count": <number>,
      "severity": "low|medium|high|critical"
    }}
  ],
  "release_readiness": {{
    "score": <number 0-100>,
    "decision": "RELEASE|CAUTION|BLOCK",
    "reasoning": [
      "<reason 1>",
      "<reason 2>",
      "<reason 3>"
    ]
  }},
  "recommendation": "<short, human-readable recommendation for the team>"
}}

**Analysis Guidelines**:
- Analyze defect trends: Look for patterns in visual defects, test failures, and validation issues across builds
- Identify hotspots: Group defects by module/component and assess severity based on the data
- Calculate release readiness: Consider test pass rates, critical defects, UI/UX validation results
- Make release decision: RELEASE (score 80+), CAUTION (score 50-79), BLOCK (score <50)
- Provide actionable recommendation: Focus on critical issues that need immediate attention

**Important**: Extract module names, defect counts, and severity levels from the actual data provided. Look for:
- Test generation history: test results, pass/fail rates, test coverage
- UI validations: visual regressions, broken components, layout issues, severity levels
- UX validations: flow issues, usability problems, screen-by-screen analysis

Analyze the data carefully and provide the comprehensive insights report in the exact JSON format specified above."""
        
        return prompt
    
    def _parse_insights_response(self, response_text):
        """Parse Gemini response for insights generation."""
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
            
            insights_report = json.loads(response_text)
            
            # Ensure all required fields exist with defaults
            if "defect_trends" not in insights_report:
                insights_report["defect_trends"] = {
                    "trend": "stable",
                    "summary": "Unable to determine defect trends"
                }
            
            if "hotspots" not in insights_report:
                insights_report["hotspots"] = []
            
            if "release_readiness" not in insights_report:
                insights_report["release_readiness"] = {
                    "score": 50,
                    "decision": "CAUTION",
                    "reasoning": ["Unable to assess release readiness"]
                }
            
            if "recommendation" not in insights_report:
                insights_report["recommendation"] = "Review data quality and re-run analysis"
            
            return insights_report
            
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON parsing failed: {str(e)}")
            # Fallback if JSON parsing fails
            return {
                "defect_trends": {
                    "trend": "stable",
                    "summary": "Failed to parse insights response"
                },
                "hotspots": [],
                "release_readiness": {
                    "score": 0,
                    "decision": "BLOCK",
                    "reasoning": ["Analysis failed - unable to parse response"]
                },
                "recommendation": "Re-run analysis with valid data",
                "error": "JSON parsing failed",
                "raw_response": response_text[:500]
            }
    