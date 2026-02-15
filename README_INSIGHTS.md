# Insights Endpoint - Complete Guide

## Overview

The `/insights` endpoint is an AI-powered quality analysis system that evaluates your software project's readiness for release. It analyzes test results, UI validations, and UX validations to provide actionable insights and clear release recommendations.

## Quick Start

### 1. Start the Server
```bash
cd octus_be
python main.py
```

### 2. Test the Endpoint
```bash
python test_insights.py
```

### 3. Make Your First Request
```bash
curl -X POST http://localhost:8080/insights \
  -H "Content-Type: application/json" \
  -d @example_insights_request.json
```

## What You Get

The endpoint provides:

1. **Defect Trends** - Are things getting better or worse?
2. **Quality Hotspots** - Which modules need attention?
3. **Release Readiness Score** - 0-100 score indicating readiness
4. **Release Decision** - Clear RELEASE/CAUTION/BLOCK recommendation
5. **Actionable Recommendations** - What to do next

## Request Format

Send a POST request with three data objects:

```json
{
  "testGenerationHistory": {
    // Your test execution history
  },
  "uiValidations": {
    // Your UI validation results
  },
  "uxValidations": {
    // Your UX validation results
  }
}
```

See `example_insights_request.json` for a complete example.

## Response Format

```json
{
  "status": "success",
  "message": "Quality insights generated successfully",
  "insights": {
    "defect_trends": {
      "trend": "increasing",
      "summary": "Test pass rate declining from 80% to 70%"
    },
    "hotspots": [
      {
        "module": "Checkout",
        "defect_count": 9,
        "severity": "critical"
      }
    ],
    "release_readiness": {
      "score": 52,
      "decision": "BLOCK",
      "reasoning": [
        "Critical UI issues in Checkout module",
        "Test pass rate below 75% threshold",
        "UX flow validation failed for checkout"
      ]
    },
    "recommendation": "Resolve critical checkout UI regressions before release"
  }
}
```

## Release Decisions

The AI makes one of three decisions:

- **RELEASE** (score 80-100): Ready for production ✅
- **CAUTION** (score 50-79): Can release with monitoring ⚠️
- **BLOCK** (score 0-49): Not ready for release ❌

## Integration Examples

### CI/CD Pipeline (GitHub Actions)

```yaml
- name: Run Quality Analysis
  run: |
    python collect_test_data.py > test_data.json
    python collect_ui_data.py > ui_data.json
    python collect_ux_data.py > ux_data.json
    
    INSIGHTS=$(curl -X POST http://api/insights \
      -H "Content-Type: application/json" \
      -d @combined_data.json)
    
    DECISION=$(echo $INSIGHTS | jq -r '.insights.release_readiness.decision')
    
    if [ "$DECISION" = "BLOCK" ]; then
      echo "Release blocked by quality analysis"
      exit 1
    fi
```

### Python Integration

```python
import requests

# Collect your data
test_data = collect_test_results()
ui_data = collect_ui_validations()
ux_data = collect_ux_validations()

# Get insights
response = requests.post('http://localhost:8080/insights', json={
    'testGenerationHistory': test_data,
    'uiValidations': ui_data,
    'uxValidations': ux_data
})

insights = response.json()['insights']

# Make decision
if insights['release_readiness']['decision'] == 'BLOCK':
    print(f"❌ Release blocked: {insights['recommendation']}")
    sys.exit(1)
elif insights['release_readiness']['decision'] == 'CAUTION':
    print(f"⚠️  Release with caution: {insights['recommendation']}")
else:
    print(f"✅ Ready to release: {insights['recommendation']}")
```

### JavaScript/Node.js Integration

```javascript
const axios = require('axios');

async function checkReleaseReadiness() {
  const testData = await collectTestResults();
  const uiData = await collectUIValidations();
  const uxData = await collectUXValidations();

  const response = await axios.post('http://localhost:8080/insights', {
    testGenerationHistory: testData,
    uiValidations: uiData,
    uxValidations: uxData
  });

  const insights = response.data.insights;
  const decision = insights.release_readiness.decision;
  const score = insights.release_readiness.score;

  console.log(`Release Score: ${score}/100`);
  console.log(`Decision: ${decision}`);
  console.log(`Recommendation: ${insights.recommendation}`);

  if (decision === 'BLOCK') {
    process.exit(1);
  }
}
```

## Data Collection Tips

### Test Generation History

Collect from your test framework:

```python
# Example: Collecting from pytest
def collect_test_results():
    return {
        "total_tests_generated": 150,
        "test_runs": [
            {
                "run_id": f"run_{i}",
                "timestamp": datetime.now().isoformat(),
                "total_tests": 150,
                "passed": results.passed,
                "failed": results.failed,
                "pass_rate": (results.passed / 150) * 100
            }
            for i, results in enumerate(test_history)
        ],
        "critical_failures": count_critical_failures(),
        "test_coverage": get_coverage_percentage()
    }
```

### UI Validations

Collect from your UI testing tools:

```python
# Example: Collecting from visual regression tests
def collect_ui_validations():
    return {
        "total_validations": len(validations),
        "validations": [
            {
                "validation_id": v.id,
                "module": v.module,
                "status": "failed" if v.has_issues else "passed",
                "severity": v.severity,
                "issues_found": len(v.issues)
            }
            for v in validations
        ],
        "overall_health": calculate_ui_health()
    }
```

### UX Validations

Collect from your UX testing:

```python
# Example: Collecting from E2E tests
def collect_ux_validations():
    return {
        "total_flows_validated": len(flows),
        "flows": [
            {
                "flow_id": f.id,
                "flow_name": f.name,
                "screens_analyzed": len(f.screens),
                "is_flow_correct": f.passed,
                "flow_quality_score": f.score,
                "issues": f.issues
            }
            for f in flows
        ],
        "overall_assessment": calculate_ux_assessment()
    }
```

## Files Reference

- **INSIGHTS_ENDPOINT.md** - Complete API documentation
- **INSIGHTS_QUICK_START.md** - Quick start guide
- **INSIGHTS_FLOW.md** - Architecture and data flow diagrams
- **INSIGHTS_SUMMARY.md** - Implementation summary
- **example_insights_request.json** - Example request data
- **test_insights.py** - Test script

## Troubleshooting

### Error: "Could not connect to server"
- Make sure the server is running: `python main.py`
- Check the port is correct (default: 8080)

### Error: "VISION_GEMINI_API_KEY not found" or "NLP_GEMINI_API_KEY not found"
- Set your API keys in `.env` file
- You need both VISION_GEMINI_API_KEY and NLP_GEMINI_API_KEY
- Copy from `.env.example` if needed

### Error: "Invalid request format"
- Ensure all three fields are present: testGenerationHistory, uiValidations, uxValidations
- Validate your JSON structure

### Low Quality Scores
- Check if you're providing enough historical data
- Ensure severity levels are set correctly
- Include detailed issue descriptions

## Best Practices

1. **Provide Historical Data** - Include multiple test runs to show trends
2. **Use Consistent Severity Levels** - Stick to: low, medium, high, critical
3. **Include Module Names** - Help the AI identify hotspots
4. **Add Detailed Descriptions** - More context = better insights
5. **Run Regularly** - Integrate into your CI/CD pipeline

## Performance

- **Response Time**: 2-5 seconds (depends on data size)
- **Max Request Size**: 10 MB
- **Rate Limiting**: None (add if needed)
- **Caching**: None (stateless)

## Security

- API keys stored in environment variables (separate keys for vision and NLP)
- No data persistence
- All processing in real-time
- Add authentication if deploying publicly

## Support

For issues or questions:

1. Check the logs: `tail -f server.log`
2. Review the documentation files
3. Test with `example_insights_request.json`
4. Verify your VISION_GEMINI_API_KEY and NLP_GEMINI_API_KEY are valid

## Next Steps

1. ✅ Test the endpoint with sample data
2. ✅ Integrate with your test framework
3. ✅ Add to your CI/CD pipeline
4. ✅ Set up notifications based on decisions
5. ✅ Create a dashboard to visualize insights

## License

Part of the Octus Backend project.
