# Latency Optimization Guide for FastAgent

## Introduction

In real-time voice agent systems, latency is a critical factor that directly impacts user experience. This guide outlines optimization strategies implemented in FastAgent to achieve ultra-low latency voice interactions. For natural conversational flow, end-to-end latency should remain below 200-300ms, from speech input to agent response.

## Core Optimization Areas

### 1. FastAPI and WebSocket Optimizations

FastAgent leverages FastAPI for its asynchronous capabilities but requires specific optimizations:

```python
# Configuration in run.py
app = FastAPI(
    title="FastAgent",
    description="Low-latency voice agent framework",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# Server configuration
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        loop="uvloop",  # Faster event loop implementation
        ws_ping_interval=5,  # Frequent ping to keep connections alive
        ws_ping_timeout=20,
        ws_max_size=16777216,  # Large message size for audio chunks
        access_log=False,  # Disable for performance
        http="h11",  # Lower overhead than HTTP/2
    )
```

**Key Optimizations:**
- **WebSocket Buffer Size**: Smaller buffers prevent audio chunk queuing
- **Ping Intervals**: Set to 5s to maintain healthy connections
- **HTTP Protocol**: Using HTTP/1.1 via h11 reduces overhead for WebSocket connections
- **Access Logging**: Disabled to reduce CPU overhead
- **UVLoop**: Faster asyncio event loop implementation than the standard library

### 2. TCP Socket-Level Optimizations

```python
async def _optimize_socket(self, websocket):
    """Apply low-level socket optimizations for minimal latency."""
    try:
        socket = websocket.client.transport.get_extra_info('socket')
        if socket:
            # Disable Nagle's algorithm
            socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            # Set socket buffer sizes
            socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            # Other optimizations based on OS
            if hasattr(socket, 'TCP_QUICKACK'):  # Linux specific
                socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_QUICKACK, 1)
    except Exception as e:
        logger.warning(f"Socket optimization failed: {e}")
```

**Key Optimizations:**
- **Disable Nagle's Algorithm**: Setting TCP_NODELAY forces immediate packet transmission
- **Buffer Sizes**: Optimized to balance between memory usage and efficient packet handling
- **Platform-Specific Optimizations**: Additional optimizations applied when available

### 3. Audio Streaming Optimizations

```python
# Configuration in app/handlers/stream_handlers.py
DEFAULT_CHUNK_SIZE = 2048  # Reduced from traditional 4096
MAX_QUEUE_SIZE = 5  # Prevents excessive buffering

async def process_audio_chunk(chunk, session_id):
    start_time = time.time()
    
    # Fast-path for audio chunks
    if len(session_queues[session_id]) < MAX_QUEUE_SIZE:
        await session_queues[session_id].put((chunk, start_time))
    else:
        # Drop old chunks if queue is full (better to skip than delay)
        try:
            session_queues[session_id].get_nowait()
            await session_queues[session_id].put((chunk, start_time))
        except asyncio.QueueEmpty:
            pass
    
    processing_time = (time.time() - start_time) * 1000
    if processing_time > 5:  # Alert on slow processing
        logger.warning(f"Audio chunk processing took {processing_time}ms")
```

**Key Optimizations:**
- **Smaller Chunk Size**: Reduced from typical 4000 to 2048 bytes for lower latency
- **Limited Queue Size**: Prevents buffering that leads to delayed processing
- **Dropping Strategy**: Better to drop old audio chunks than process delayed ones
- **Parallel Processing**: Using asyncio tasks for concurrent handling
- **Fast-Path Processing**: Minimal validation for audio chunks

### 4. Memory and Context Management

The FSA architecture enables efficient memory management:

```python
class ConversationContext:
    def __init__(self, max_history=10):
        self.current_state = "greeting"
        self.salient_facts = {}
        self.conversation_history = deque(maxlen=max_history)
        self.user_profile = {}
        
    def update_context(self, user_utterance, agent_response, state=None):
        # Only store essential information
        self.conversation_history.append({
            "user": user_utterance[:100],  # Truncate to save memory
            "agent": agent_response[:100],
            "timestamp": time.time()
        })
        if state:
            self.current_state = state
```

**Key Optimizations:**
- **Bounded History**: Fixed-size deque prevents unbounded memory growth
- **Selective Persistence**: Only storing essential information
- **Truncation**: Long utterances are truncated to conserve memory
- **State-Based Filtering**: Only relevant context is passed to each state

### 5. LLM Integration Optimizations

```python
async def get_llm_response(text, context, state):
    # Only include required context for current state
    relevant_context = _filter_context_for_state(context, state)
    
    # Use streamed responses for faster first token
    response_stream = await llm_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": STATE_PROMPTS[state]},
            {"role": "user", "content": f"Context: {relevant_context}\n\nUser: {text}"}
        ],
        stream=True,
        temperature=0.7,
        max_tokens=150,  # Limit token generation
        timeout=2.0,  # Hard timeout for LLM requests
    )
    
    # Process streamed response for immediate voice synthesis
    first_chunk_time = None
    response_text = ""
    
    async for chunk in response_stream:
        if not first_chunk_time:
            first_chunk_time = time.time()
            # Start TTS with first chunk immediately
            
        if chunk.choices[0].delta.content:
            response_text += chunk.choices[0].delta.content
    
    return response_text
```

**Key Optimizations:**
- **Streaming Responses**: Enable immediate processing of first tokens
- **Context Filtering**: Only sending relevant context to the LLM
- **Token Limits**: Restricting response length for faster processing
- **Hard Timeouts**: Preventing hung requests
- **Parallel TTS**: Starting voice synthesis before full response is generated

### 6. Voice Synthesis Optimization

```python
class VoiceSynthesizer:
    def __init__(self):
        self.tts_client = TTSClient()
        self.audio_queue = asyncio.Queue(maxsize=10)
        self.chunk_size = 1024  # Smaller chunks for streaming
        
    async def synthesize_and_stream(self, text, websocket):
        # Split text at natural breakpoints for faster streaming
        segments = self._segment_text(text)
        
        tasks = []
        for segment in segments:
            # Create task for each segment to synthesize in parallel
            task = asyncio.create_task(self._synthesize_segment(segment))
            tasks.append(task)
            
        # Stream audio as soon as first segment is ready
        for task in asyncio.as_completed(tasks):
            audio = await task
            await self._stream_audio(audio, websocket)
    
    def _segment_text(self, text):
        """Split text at natural breakpoints like periods and commas."""
        # Implementation details
```

**Key Optimizations:**
- **Text Segmentation**: Breaking responses at natural points for faster initial playback
- **Parallel Synthesis**: Processing multiple segments concurrently
- **Progressive Streaming**: Sending audio as soon as each segment is synthesized
- **Smaller Audio Chunks**: Optimized for network transmission

## Latency Monitoring and Debugging

FastAgent includes built-in latency monitoring:

```python
@app.get("/health")
async def health_check():
    """Health check endpoint with latency metrics."""
    global latency_metrics
    
    # Calculate statistics
    stats = {
        "status": "healthy",
        "latency": {
            "avg_ms": sum(latency_metrics) / len(latency_metrics) if latency_metrics else 0,
            "min_ms": min(latency_metrics) if latency_metrics else 0,
            "max_ms": max(latency_metrics) if latency_metrics else 0,
            "p95_ms": percentile(latency_metrics, 95) if latency_metrics else 0,
            "p99_ms": percentile(latency_metrics, 99) if latency_metrics else 0,
        },
        "uptime_seconds": time.time() - start_time,
        "active_connections": len(active_connections),
    }
    
    return stats
```

### Latency Testing Tools

FastAgent provides a specialized script for latency testing:

```bash
# Using PowerShell to run latency test
python .\latency_test.py --duration 60 --rate 5
```

The test simulates real voice traffic and provides statistical analysis of system performance.

## Deployment Recommendations

For optimal latency in production environments:

1. **Hardware Requirements**:
   - CPU: At least 4 dedicated cores per instance
   - Memory: Minimum 8GB RAM
   - Network: Low-latency connection with minimal jitter

2. **Network Configuration**:
   - Deploy servers close to voice infrastructure
   - Use dedicated network interfaces when possible
   - Implement QoS to prioritize voice traffic

3. **Scaling Strategy**:
   - Horizontal scaling with load balancing
   - Keep individual instance load below 70% CPU utilization
   - Monitor latency metrics to trigger auto-scaling

4. **Environment Tuning**:
   - OS-level TCP optimizations (sysctls on Linux)
   - Process priority adjustments
   - Filesystem optimizations for log writing

## Advanced Optimization Techniques

For systems requiring ultra-low latency (sub-100ms):

1. **Custom WebSocket Implementation**: 
   - Replace standard libraries with optimized implementations
   - Implement custom frame handling for audio data

2. **Memory-Mapped Audio Buffers**:
   - Reduce memory copies between system components
   - Use shared memory for inter-process communication

3. **SIMD Optimizations**:
   - Leverage CPU vector instructions for audio processing
   - Implement critical sections in optimized C/C++ extensions

4. **Edge Deployment**:
   - Deploy on edge servers close to end-users
   - Use CDN infrastructure for global distribution

## Conclusion

Achieving ultra-low latency in voice agent systems requires a holistic approach spanning network configuration, code optimization, and efficient resource management. FastAgent's architecture provides the foundation for sub-300ms interactions, with opportunities for further optimization based on specific deployment scenarios.

By following these guidelines, developers can create voice agents that provide natural, responsive conversations indistinguishable from human interactions. 