# Model Comparison Guide

## Overview

Sibyl supports local open-source LLMs running via Ollama. This guide helps you understand the characteristics of different models and choose the best one for your needs.

## Supported Models

### Llama 3.2 (Meta)

**Models**: `llama3.2:1b`, `llama3.2:3b`

**Strengths**:
- Excellent general capabilities
- Multiple size options for different hardware
- Strong reasoning abilities
- Well-optimized for local execution

**Best For**:
- General academic paper review
- Balanced performance and quality
- Users with moderate hardware

**Typical Characteristics**:
- Provides thorough, balanced analysis
- Good at identifying both strengths and weaknesses
- Reliable across different paper types

**Hardware**: 
- 1B: 8GB RAM minimum
- 3B: 16GB RAM recommended

### Mistral (Mistral AI)

**Model**: `mistral:7b`

**Strengths**:
- Excellent reasoning and analytical capabilities
- Strong attention to technical details
- Good at identifying subtle issues
- Fast inference relative to size

**Best For**:
- Technical papers requiring deep analysis
- Complex methodologies
- When detail-oriented feedback is crucial

**Typical Characteristics**:
- Thorough and methodical reviews
- May be more critical than other models
- Excellent at logical reasoning

**Hardware**: 16GB RAM recommended, 32GB optimal

### Phi-3 (Microsoft)

**Models**: `phi3:mini` (3.8B), `phi3:medium` (14B)

**Strengths**:
- Impressive performance for size
- Efficient resource usage
- Strong language understanding
- Good general knowledge

**Best For**:
- Users with limited hardware
- Quick reviews
- General assessment needs

**Typical Characteristics**:
- Concise, focused reviews
- Good balance of quality and speed
- Efficient on consumer hardware

**Hardware**: 
- Mini: 8GB RAM
- Medium: 24GB RAM

### Gemma 2 (Google)

**Models**: `gemma2:2b`, `gemma2:9b`

**Strengths**:
- Well-balanced capabilities
- Good instruction following
- Efficient architecture
- Strong performance across tasks

**Best For**:
- General paper review
- Multi-domain research
- Balanced assessments

**Typical Characteristics**:
- Balanced, fair reviews
- Good contextual understanding
- Reliable outputs

**Hardware**:
- 2B: 8GB RAM
- 9B: 16-24GB RAM

### Qwen 2.5 (Alibaba)

**Models**: Various sizes from 0.5B to 72B

**Strengths**:
- Strong multilingual capabilities
- Excellent reasoning abilities
- Good at structured outputs
- Multiple size options

**Best For**:
- Papers in multiple languages
- Complex reasoning tasks
- Structured analysis needs

**Typical Characteristics**:
- Detailed, structured reviews
- Good at following complex instructions
- Strong analytical capabilities

**Hardware**: Varies by size (8GB to 64GB+ RAM)

## Comparison Strategy

### When to Compare Multiple Models

**Sequential Comparison Beneficial**:
- High-stakes decisions (acceptance/rejection)
- Controversial or novel work
- When diverse perspectives are valuable
- For comprehensive evaluation

**Single Model Sufficient**:
- Preliminary reviews of your own work
- Quick quality checks
- Informal assessments
- When time/resources are limited

### Recommended Approaches

**Best Quality**: Mistral or Llama 3.2:3b
- Highest quality reviews
- Best for critical decisions
- Requires adequate hardware

**Balanced**: Llama 3.2:1b or Phi-3 Mini
- Good balance of quality and speed
- Sufficient for most purposes
- Works on modest hardware

**Fast/Efficient**: Phi-3 Mini or Gemma 2:2b
- Quick turnaround
- Lower resource requirements
- Good for initial screening

## Interpreting Results

### Score Tendencies

Different models may have different scoring tendencies:

- **Mistral**: Tends toward detailed, critical analysis
- **Llama**: Balanced, uses full score range
- **Phi-3**: Concise, focused feedback
- **Gemma**: Balanced and fair
- **Qwen**: Structured, detailed responses

### Focus Areas

- **Mistral**: Heavy emphasis on methodology and rigor
- **Llama**: Balanced across all criteria
- **Phi-3**: Focuses on key issues
- **Gemma**: Good at practical implications
- **Qwen**: Strong on structured analysis

## Best Practices

### Model Selection Tips

1. **Match hardware to model**: Don't choose a model too large for your system
2. **Consider paper complexity**: Use larger models for complex papers
3. **Experiment**: Try different models to find what works for your domain
4. **Document preferences**: Track which models work best for your field

### Optimizing for Your Needs

**For Speed**: Phi-3 Mini, Gemma 2:2b, Llama 3.2:1b
**For Quality**: Mistral, Llama 3.2:3b, Qwen (larger variants)
**For Balance**: Llama 3.2:3b, Gemma 2:9b
**For Limited Hardware**: Phi-3 Mini, Llama 3.2:1b

## Performance Metrics

Based on typical usage:

| Model | Speed | Hardware | Quality | Detail | Size |
|-------|-------|----------|---------|--------|------|
| Llama 3.2:1b | ⭐⭐⭐⭐⭐ | 8GB RAM | ⭐⭐⭐ | ⭐⭐⭐ | 1B |
| Llama 3.2:3b | ⭐⭐⭐⭐ | 16GB RAM | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 3B |
| Mistral | ⭐⭐⭐ | 16GB RAM | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 7B |
| Phi-3 Mini | ⭐⭐⭐⭐⭐ | 8GB RAM | ⭐⭐⭐⭐ | ⭐⭐⭐ | 3.8B |
| Gemma 2:2b | ⭐⭐⭐⭐⭐ | 8GB RAM | ⭐⭐⭐ | ⭐⭐⭐ | 2B |
| Gemma 2:9b | ⭐⭐⭐ | 16-24GB RAM | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 9B |

## Hardware Considerations

### GPU Acceleration

Models run significantly faster with GPU acceleration:
- **NVIDIA GPUs**: Best support via CUDA
- **Apple Silicon**: Good support via Metal
- **AMD GPUs**: Growing support via ROCm

### Memory Requirements

Approximate RAM needed (for Q4 quantization):
- **1-2B models**: 4-8GB
- **3-4B models**: 8-12GB
- **7-8B models**: 12-20GB
- **13-14B models**: 24-32GB
- **30B+ models**: 64GB+

## Future Model Support

Ollama regularly adds support for new models. Check `ollama list` for available models or visit [ollama.ai/library](https://ollama.ai/library) for the complete list.

## Conclusion

The best model depends on your specific needs, hardware constraints, and use case. Start with Llama 3.2 or Phi-3 Mini to understand their characteristics, then experiment with others based on your requirements.
