import asyncio
import base64
import json
import time
import uuid
from pathlib import Path

import websockets

from validate.validate import AudioRecorder, load_audio_chunks

USER_PHRASES = [
    "replacement_card_1.wav",
    "replacement_card_2.wav",
    "replacement_card_3.wav",
    "replacement_card_4.wav",
    "replacement_card_5.wav",
]


async def validate_replacement_card_flow(
    WS_URL, AUDIO_FILE_PATH, load_audio_chunks, AudioRecorder, TIMEOUT_SECONDS=15
):
    """Validate the replacement card flow: session.initiate → session.accepted → playStream.start → playStream.stop."""
    print(f"\n[Replacement Card Flow] Testing back-and-forth conversation...")
    print(f"Connecting to {WS_URL}...")
    
    # Base path for audio files (assuming they're in the same directory as AUDIO_FILE_PATH)
    audio_base_path = Path(AUDIO_FILE_PATH).parent

    try:
        async with websockets.connect(WS_URL, ping_interval=5, ping_timeout=20) as ws:
            print("✅ WebSocket connection established")

            # First establish a session
            conversation_id = str(uuid.uuid4())
            session_initiate = {
                "type": "session.initiate",
                "conversationId": conversation_id,
                "expectAudioMessages": True,
                "botName": "ReplacementCardBot",
                "caller": "+15551234567",
                "supportedMediaFormats": ["raw/lpcm16"],
            }

            await ws.send(json.dumps(session_initiate))
            print(f"✅ Sent session.initiate with conversationId: {conversation_id}")

            # Initialize audio recorder
            recorder = AudioRecorder(f"replacement_card_{conversation_id[:8]}")

            # Wait for session.accepted and initial bot greeting
            session_accepted = False
            initial_bot_response_complete = False
            
            print("Waiting for session.accepted and initial bot greeting...")
            
            # Process initial session establishment and bot greeting
            for attempt in range(60):  # 30 seconds
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
                        # Record the bot's audio
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

            # Now process each user phrase in sequence
            successful_exchanges = 0
            
            for phrase_index, phrase_file in enumerate(USER_PHRASES, 1):
                print(f"\n--- Exchange {phrase_index}/5: {phrase_file} ---")
                
                # Check if the audio file exists
                phrase_path = audio_base_path / phrase_file
                if not phrase_path.exists():
                    print(f"⚠️ Audio file not found: {phrase_path}, using default audio instead")
                    phrase_path = AUDIO_FILE_PATH
                
                # Load audio chunks for this phrase
                audio_chunks = load_audio_chunks(phrase_path)
                if not audio_chunks:
                    print(f"❌ Failed to load audio for {phrase_file}")
                    continue

                # Start user stream
                user_stream_start = {
                    "type": "userStream.start",
                    "conversationId": conversation_id,
                }
                await ws.send(json.dumps(user_stream_start))
                print("✅ Sent userStream.start")

                # Wait for userStream.started
                stream_started = False
                for attempt in range(20):  # 10 seconds
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                        response_data = json.loads(response)
                        msg_type = response_data.get("type")

                        if msg_type == "userStream.started":
                            stream_started = True
                            print("✅ Received userStream.started")
                            break
                        elif msg_type == "playStream.chunk":
                            # Continue recording any ongoing bot audio
                            audio_chunk = response_data.get("audioChunk")
                            if audio_chunk:
                                recorder.record_bot_audio(audio_chunk)

                    except asyncio.TimeoutError:
                        continue

                if not stream_started:
                    print(f"❌ userStream.started not received for phrase {phrase_index}")
                    continue

                # Send user audio chunks
                print(f"🎤 Playing user phrase: {phrase_file} ({len(audio_chunks)} chunks)")
                for i, chunk in enumerate(audio_chunks):
                    # Record the outgoing user audio
                    recorder.record_user_audio(chunk)

                    audio_chunk_msg = {
                        "type": "userStream.chunk",
                        "conversationId": conversation_id,
                        "audioChunk": chunk,
                    }
                    await ws.send(json.dumps(audio_chunk_msg))
                    if i % 10 == 0 or i == len(audio_chunks) - 1:
                        print(f"   Sent chunk {i+1}/{len(audio_chunks)}")
                    await asyncio.sleep(0.01)  # Small delay between chunks

                # Wait a moment before stopping stream
                await asyncio.sleep(0.2)

                # Stop user stream
                user_stream_stop = {
                    "type": "userStream.stop",
                    "conversationId": conversation_id,
                }
                await ws.send(json.dumps(user_stream_stop))
                print("✅ Sent userStream.stop")

                # Wait for bot response
                stream_stopped = False
                bot_started_response = False
                bot_finished_response = False
                bot_chunk_count = 0

                print("🤖 Waiting for bot response...")
                
                # Process messages until bot response is complete
                for attempt in range(60):  # 30 seconds for bot response
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                        response_data = json.loads(response)
                        msg_type = response_data.get("type")

                        if msg_type == "userStream.stopped":
                            stream_stopped = True
                            print("✅ Received userStream.stopped")

                        elif msg_type == "playStream.start":
                            bot_started_response = True
                            print("✅ Bot started responding")

                        elif msg_type == "playStream.chunk":
                            if not bot_started_response:
                                bot_started_response = True
                                print("✅ Bot started responding")
                            
                            bot_chunk_count += 1
                            # Record the bot's audio response
                            audio_chunk = response_data.get("audioChunk")
                            if audio_chunk:
                                recorder.record_bot_audio(audio_chunk)
                            
                            if bot_chunk_count % 20 == 0:
                                print(f"   Receiving bot audio... ({bot_chunk_count} chunks)")

                        elif msg_type == "playStream.stop":
                            bot_finished_response = True
                            print(f"✅ Bot finished responding ({bot_chunk_count} chunks)")
                            break

                    except asyncio.TimeoutError:
                        continue

                # Check if this exchange was successful
                if stream_stopped and bot_started_response and bot_finished_response:
                    successful_exchanges += 1
                    print(f"✅ Exchange {phrase_index} completed successfully")
                else:
                    print(f"❌ Exchange {phrase_index} failed:")
                    print(f"   Stream stopped: {stream_stopped}")
                    print(f"   Bot responded: {bot_started_response}")
                    print(f"   Bot finished: {bot_finished_response}")

                # Small pause between exchanges
                await asyncio.sleep(1)

            # Final summary
            print(f"\n--- Replacement Card Flow Summary ---")
            print(f"✅ Successful exchanges: {successful_exchanges}/{len(USER_PHRASES)}")
            
            # End the session gracefully
            try:
                session_end = {
                    "type": "session.end",
                    "conversationId": conversation_id,
                    "reasonCode": "normal",
                    "reason": "Replacement card flow validation completed",
                }
                await ws.send(json.dumps(session_end))
                print("✅ Sent session.end event")
                await asyncio.sleep(1)
            except websockets.exceptions.ConnectionClosed:
                print("❌ Connection closed before ending session")

            # Close the recorder and save all audio files
            recorder.close()
            
            # Return success if we completed at least 80% of exchanges
            success = successful_exchanges >= len(USER_PHRASES) * 0.8
            if success:
                print("✅ Replacement card flow validation: PASSED")
            else:
                print("❌ Replacement card flow validation: FAILED")
            
            return success

    except ConnectionRefusedError:
        print("❌ Connection refused. Is the server running?")
        return False
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ Connection closed unexpectedly: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during replacement card flow validation: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False


async def main():
    """Run the replacement card flow validation standalone."""
    import os
    from pathlib import Path
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Configuration
    HOST = os.getenv("HOST", "localhost")
    PORT = int(os.getenv("PORT", "8000"))
    WS_URL = f"ws://{HOST}:{PORT}/voice-bot"
    
    # Path to default audio file
    AUDIO_FILE_PATH = Path(__file__).parent.parent / "static" / "tell_me_about_your_bank.wav"
    
    print("=== Replacement Card Flow Validation ===")
    
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
    success = await validate_replacement_card_flow(
        WS_URL=WS_URL,
        AUDIO_FILE_PATH=AUDIO_FILE_PATH,
        load_audio_chunks=load_audio_chunks,
        AudioRecorder=AudioRecorder,
        TIMEOUT_SECONDS=15
    )
    
    if success:
        print("\n✅ REPLACEMENT CARD FLOW VALIDATION PASSED!")
    else:
        print("\n❌ REPLACEMENT CARD FLOW VALIDATION FAILED!")


if __name__ == "__main__":
    asyncio.run(main())
