"""
Test script for the /insights endpoint
"""
import requests
import json

# Sample test data with new format
test_data = {
    "testGenerationHistory": {
        "total_tests_generated": 150,
        "test_runs": [
            {
                "run_id": "run_001",
                "timestamp": "2024-01-15T10:00:00Z",
                "total_tests": 150,
                "passed": 120,
                "failed": 30,
                "pass_rate": 80
            },
            {
                "run_id": "run_002",
                "timestamp": "2024-01-16T10:00:00Z",
                "total_tests": 150,
                "passed": 110,
                "failed": 40,
                "pass_rate": 73
            },
            {
                "run_id": "run_003",
                "timestamp": "2024-01-17T10:00:00Z",
                "total_tests": 150,
                "passed": 105,
                "failed": 45,
                "pass_rate": 70
            }
        ],
        "critical_failures": 8,
        "test_coverage": 85
    },
    "uiValidations": {
        "total_validations": 25,
        "validations": [
            {
                "validation_id": "ui_001",
                "module": "Checkout",
                "status": "failed",
                "severity": "critical",
                "issues_found": 9,
                "broken_components": 3,
                "layout_issues": 4,
                "color_contrast_issues": 2
            },
            {
                "validation_id": "ui_002",
                "module": "Payment",
                "status": "failed",
                "severity": "high",
                "issues_found": 6,
                "broken_components": 2,
                "layout_issues": 3,
                "color_contrast_issues": 1
            },
            {
                "validation_id": "ui_003",
                "module": "Login",
                "status": "passed",
                "severity": "low",
                "issues_found": 1,
                "broken_components": 0,
                "layout_issues": 1,
                "color_contrast_issues": 0
            }
        ],
        "overall_health": {
            "status": "critical",
            "health_score": 52,
            "total_issues_found": 16,
            "critical_issues": 5
        }
    },
    "uxValidations": {
        "total_flows_validated": 5,
        "flows": [
            {
                "flow_id": "ux_001",
                "flow_name": "Checkout Flow",
                "screens_analyzed": 5,
                "is_flow_correct": False,
                "flow_quality_score": 45,
                "issues": [
                    {
                        "type": "missing_field",
                        "severity": "critical",
                        "description": "Payment confirmation missing on final screen"
                    },
                    {
                        "type": "navigation_issue",
                        "severity": "high",
                        "description": "Back button inconsistent across screens"
                    }
                ]
            },
            {
                "flow_id": "ux_002",
                "flow_name": "Login Flow",
                "screens_analyzed": 3,
                "is_flow_correct": True,
                "flow_quality_score": 85,
                "issues": []
            }
        ],
        "overall_assessment": {
            "average_quality_score": 65,
            "flows_with_issues": 1,
            "total_critical_issues": 1
        }
    }
}

def test_insights_endpoint():
    """Test the /insights endpoint"""
    url = "http://localhost:8080/insights"
    
    print("Testing /insights endpoint...")
    print(f"Sending request to: {url}")
    print(f"Request data: {json.dumps(test_data, indent=2)}")
    
    try:
        response = requests.post(url, json=test_data)
        
        print(f"\nResponse Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nSuccess! Response:")
            print(json.dumps(result, indent=2))
            
            # Validate response structure
            if "insights" in result:
                insights = result["insights"]
                print("\n=== Insights Summary ===")
                print(f"Defect Trend: {insights.get('defect_trends', {}).get('trend', 'N/A')}")
                print(f"Release Score: {insights.get('release_readiness', {}).get('score', 'N/A')}")
                print(f"Release Decision: {insights.get('release_readiness', {}).get('decision', 'N/A')}")
                print(f"Recommendation: {insights.get('recommendation', 'N/A')}")
                print(f"Hotspots: {len(insights.get('hotspots', []))}")
                
                # Print hotspots
                if insights.get('hotspots'):
                    print("\n=== Quality Hotspots ===")
                    for hotspot in insights['hotspots']:
                        print(f"  - {hotspot.get('module', 'Unknown')}: {hotspot.get('defect_count', 0)} defects ({hotspot.get('severity', 'unknown')} severity)")
        else:
            print(f"\nError Response:")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to server. Make sure the server is running on http://localhost:8080")
    except Exception as e:
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    test_insights_endpoint()
