import asyncio
import base64
import json
from pathlib import Path
import sys
import uuid
import websockets

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))


from validate import AudioRecorder, load_audio_chunks

async def validate_function_calling_flow(
    WS_URL, AUDIO_FILE_PATH, load_audio_chunks, AudioRecorder, TIMEOUT_SECONDS=20
):
    """Validate function calling: session.initiate → user message → function call → function result → bot response."""
    print(f"\n[Function Calling Flow] Testing function calling...")
    print(f"Connecting to {WS_URL}...")

    try:
        async with websockets.connect(WS_URL, ping_interval=5, ping_timeout=20) as ws:
            print("✅ WebSocket connection established")

            # Establish a session
            conversation_id = str(uuid.uuid4())
            session_initiate = {
                "type": "session.initiate",
                "conversationId": conversation_id,
                "expectAudioMessages": True,
                "botName": "FunctionBot",
                "caller": "+15551234567",
                "supportedMediaFormats": ["raw/lpcm16"],
            }
            await ws.send(json.dumps(session_initiate))
            print(f"✅ Sent session.initiate with conversationId: {conversation_id}")

            # Initialize audio recorder
            recorder = AudioRecorder(f"function_call_{conversation_id[:8]}")

            # Wait for session.accepted and initial bot greeting
            session_accepted = False
            initial_bot_response_complete = False
            print("Waiting for session.accepted and initial bot greeting...")
            for attempt in range(60):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    response_data = json.loads(response)
                    msg_type = response_data.get("type")
                    if msg_type == "session.accepted":
                        session_accepted = True
                        print("✅ Session accepted")
                    elif msg_type == "playStream.start":
                        print("✅ Bot started speaking (initial greeting)")
                    elif msg_type == "playStream.chunk":
                        audio_chunk = response_data.get("audioChunk")
                        if audio_chunk:
                            recorder.record_bot_audio(audio_chunk)
                    elif msg_type == "playStream.stop":
                        print("✅ Bot finished initial greeting")
                        initial_bot_response_complete = True
                        break
                except asyncio.TimeoutError:
                    continue
            if not session_accepted:
                print("❌ Session establishment failed")
                recorder.close()
                return False
            if not initial_bot_response_complete:
                print("❌ Initial bot greeting not received")
                recorder.close()
                return False

            # Send a user message that should trigger a function call (e.g., get_balance)
            print("\n--- Sending user message to trigger function call ---")
            user_message = {
                "type": "userStream.start",
                "conversationId": conversation_id,
            }
            await ws.send(json.dumps(user_message))
            await asyncio.sleep(0.1)

            # Use a short audio file or silence chunk for the user message
            # (Assume AUDIO_FILE_PATH is a valid short prompt, or use silence)
            audio_chunks = load_audio_chunks(AUDIO_FILE_PATH)
            if not audio_chunks:
                silence_chunk = base64.b64encode(b"\x00" * 3200).decode("utf-8")
                audio_chunks = [silence_chunk]
            for chunk in audio_chunks:
                recorder.record_user_audio(chunk)
                audio_chunk_msg = {
                    "type": "userStream.chunk",
                    "conversationId": conversation_id,
                    "audioChunk": chunk,
                }
                await ws.send(json.dumps(audio_chunk_msg))
                await asyncio.sleep(0.01)
            await asyncio.sleep(0.2)
            user_stream_stop = {
                "type": "userStream.stop",
                "conversationId": conversation_id,
            }
            await ws.send(json.dumps(user_stream_stop))
            print("✅ Sent userStream.stop")

            # Wait for function call and function result
            function_call_observed = False
            function_result_observed = False
            bot_started_response = False
            bot_finished_response = False
            bot_chunk_count = 0
            print("\n--- Waiting for function call and result ---")
            for attempt in range(TIMEOUT_SECONDS * 2):
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    response_data = json.loads(response)
                    msg_type = response_data.get("type")
                    if msg_type == "userStream.stopped":
                        print("✅ Received userStream.stopped")
                    elif msg_type == "playStream.start":
                        bot_started_response = True
                        print("✅ Bot started responding (after function call)")
                    elif msg_type == "playStream.chunk":
                        bot_chunk_count += 1
                        audio_chunk = response_data.get("audioChunk")
                        if audio_chunk:
                            recorder.record_bot_audio(audio_chunk)
                        if bot_chunk_count % 10 == 0:
                            print(f"   Receiving bot audio... ({bot_chunk_count} chunks)")
                    elif msg_type == "playStream.stop":
                        bot_finished_response = True
                        print(f"✅ Bot finished responding ({bot_chunk_count} chunks)")
                        break
                    # Look for function call and result in the event stream
                    elif msg_type == "function_call":
                        function_call_observed = True
                        print(f"✅ Function call observed: {response_data}")
                    elif msg_type == "function_result":
                        function_result_observed = True
                        print(f"✅ Function result observed: {response_data}")
                    # Some bridges may log function call as conversation.item.create with type 'function_result'
                    elif msg_type == "conversation.item.create":
                        item = response_data.get("item", {})
                        if item.get("type") == "function_result":
                            function_result_observed = True
                            print(f"✅ Function result observed in conversation.item.create: {item}")
                except asyncio.TimeoutError:
                    continue
            # Final summary
            print("\n--- Function Calling Flow Summary ---")
            print(f"✅ Function call observed: {function_call_observed}")
            print(f"✅ Function result observed: {function_result_observed}")
            print(f"✅ Bot responded: {bot_started_response} → {bot_finished_response}")
            recorder.close()
            success = function_result_observed and bot_started_response and bot_finished_response
            if success:
                print("✅ Function calling validation: PASSED")
            else:
                print("❌ Function calling validation: FAILED")
            return success
    except ConnectionRefusedError:
        print("❌ Connection refused. Is the server running?")
        return False
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ Connection closed unexpectedly: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during function calling validation: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

async def main():
    """Run the function calling validation standalone."""
    import os
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv()
    HOST = os.getenv("HOST", "localhost")
    PORT = int(os.getenv("PORT", "8000"))
    WS_URL = f"ws://{HOST}:{PORT}/voice-bot"
    AUDIO_FILE_PATH = Path(__file__).parent.parent / "static" / "what_is_my_balance.wav"
    print("=== Function Calling Validation ===")
    # Check if server is running
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((HOST, PORT))
    sock.close()
    if result != 0:
        print(f"❌ Server not found at {HOST}:{PORT}")
        print("Please start the server with: python run.py")
        return
    # Run the validation
    success = await validate_function_calling_flow(
        WS_URL=WS_URL,
        AUDIO_FILE_PATH=AUDIO_FILE_PATH,
        load_audio_chunks=load_audio_chunks,
        AudioRecorder=AudioRecorder,
        TIMEOUT_SECONDS=20
    )
    if success:
        print("\n✅ FUNCTION CALLING VALIDATION PASSED!")
    else:
        print("\n❌ FUNCTION CALLING VALIDATION FAILED!")

if __name__ == "__main__":
    asyncio.run(main()) 