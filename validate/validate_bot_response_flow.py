"""
Bot response flow validation for TelephonyRealtimeBridge.

This module provides the async function validate_bot_response_flow, which tests the bot's playStream message sequence:
- playStream.start → playStream.chunk → playStream.stop

Depends on AudioRecorder and load_audio_chunks from validate.validate.
"""

import asyncio
import base64
import json
import websockets
import uuid

async def validate_bot_response_flow(
    WS_URL,
    AUDIO_FILE_PATH,
    load_audio_chunks,
    AudioRecorder,
    TIMEOUT_SECONDS=15
):
    """Validate the bot response flow: playStream.start to playStream.stop."""
    print(f"\n[3/3] Testing bot response flow (playStream)...")
    print(f"Connecting to {WS_URL}...")

    try:
        async with websockets.connect(WS_URL, ping_interval=5, ping_timeout=20) as ws:
            print("✅ WebSocket connection established")

            # First establish a session
            conversation_id = str(uuid.uuid4())
            session_initiate = {
                "type": "session.initiate",
                "conversationId": conversation_id,
                "expectAudioMessages": True,
                "botName": "TestBot",
                "caller": "+15551234567",
                "supportedMediaFormats": ["raw/lpcm16"],
            }

            await ws.send(json.dumps(session_initiate))
            print(f"Sent session.initiate with conversationId: {conversation_id}")

            # Initialize audio recorder
            recorder = AudioRecorder(conversation_id[:8])

            # Wait for session.accepted and process all incoming messages
            session_accepted = False
            play_stream_started = False
            stream_id = None
            play_stream_chunks_received = False
            chunk_count = 0
            first_response_complete = False

            print("Waiting for session.accepted and bot's initial response...")
            print("   Note: Bot will start speaking immediately after session is established")

            # Process all messages in a single loop to avoid dropping any
            for attempt in range(120):  # 60 seconds total (120 * 0.5s)
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    response_data = json.loads(response)
                    msg_type = response_data.get("type")

                    # Print progress every 10 seconds
                    if attempt % 20 == 0 and attempt > 0:
                        print(f"   Processing messages... ({attempt * 0.5:.1f}s elapsed)")

                    if msg_type == "session.accepted":
                        session_accepted = True
                        print("✅ Session accepted")

                    elif msg_type == "playStream.start":
                        if not play_stream_started:
                            play_stream_started = True
                            stream_id = response_data.get("streamId")
                            print(f"✅ Received playStream.start with streamId: {stream_id}")

                    elif msg_type == "playStream.chunk":
                        if not play_stream_chunks_received:
                            print(f"✅ Started receiving playStream.chunk messages (bot's initial response)")
                            play_stream_chunks_received = True
                        chunk_count += 1

                        # Record the audio chunk
                        audio_chunk = response_data.get("audioChunk")
                        if audio_chunk:
                            recorder.record_bot_audio(audio_chunk)

                        # Log progress every 20 chunks
                        if chunk_count % 20 == 0:
                            print(f"   Received {chunk_count} audio chunks so far...")

                    elif msg_type == "playStream.stop":
                        print(f"✅ Received playStream.stop for streamId: {response_data.get('streamId')}")
                        if not first_response_complete:
                            first_response_complete = True
                            print(f"   Bot's initial response complete - received {chunk_count} audio chunks")
                            break

                    # Continue processing other message types silently

                except asyncio.TimeoutError:
                    # If we have session accepted and received some chunks, we can continue
                    if (
                        session_accepted
                        and play_stream_chunks_received
                        and first_response_complete
                    ):
                        break
                    continue
                except websockets.exceptions.ConnectionClosed:
                    print("❌ Connection closed while processing initial messages")
                    recorder.close()
                    return False

            if not session_accepted:
                print("❌ Session establishment failed")
                recorder.close()
                return False

            if not play_stream_started:
                print("❌ ERROR: Bot did not speak first - playStream.start was not received")
                recorder.close()
                return False

            if not play_stream_chunks_received:
                print("❌ ERROR: No playStream.chunk messages were received from bot's initial response")
                recorder.close()
                return False

            # Load audio chunks
            audio_chunks = load_audio_chunks(AUDIO_FILE_PATH)
            if not audio_chunks:
                print("❌ No audio chunks loaded, using silence instead")
                # Create a minimum valid chunk of silence (100ms)
                silence_chunk = base64.b64encode(b"\x00" * 3200).decode("utf-8")
                audio_chunks = [silence_chunk]

            # Send audio to trigger a bot response
            user_stream_start = {
                "type": "userStream.start",
                "conversationId": conversation_id,
            }
            await ws.send(json.dumps(user_stream_start))
            print("✅ Sent userStream.start")

            # Wait for userStream.started and process all messages
            stream_started = False
            play_stream_started_2 = False
            stream_id_2 = None
            play_stream_chunks_received_2 = False
            chunk_count_2 = 0
            stream_stopped = False
            second_response_complete = False

            print("Processing user stream and waiting for second bot response...")

            # Process all messages efficiently
            for attempt in range(120):  # 60 seconds total
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    response_data = json.loads(response)
                    msg_type = response_data.get("type")

                    if msg_type == "userStream.started":
                        stream_started = True
                        print("✅ Received userStream.started")

                        # Now send audio chunks
                        print(f"Sending {len(audio_chunks)} audio chunks to trigger bot response...")
                        for i, chunk in enumerate(audio_chunks):
                            # Record the outgoing user audio
                            recorder.record_user_audio(chunk)

                            audio_chunk = {
                                "type": "userStream.chunk",
                                "conversationId": conversation_id,
                                "audioChunk": chunk,
                            }
                            await ws.send(json.dumps(audio_chunk))
                            if i % 10 == 0 or i == len(audio_chunks) - 1:
                                print(f"   Sent audio chunk {i+1}/{len(audio_chunks)}")
                            await asyncio.sleep(0.01)  # 10ms delay between chunks

                        # Wait a moment before sending stop to ensure all audio is processed
                        await asyncio.sleep(0.2)

                        # Send userStream.stop
                        user_stream_stop = {
                            "type": "userStream.stop",
                            "conversationId": conversation_id,
                        }
                        await ws.send(json.dumps(user_stream_stop))
                        print("✅ Sent userStream.stop")

                    elif msg_type == "userStream.stopped":
                        stream_stopped = True
                        print("✅ Received userStream.stopped")

                    elif msg_type == "playStream.start":
                        if stream_stopped and not play_stream_started_2:
                            play_stream_started_2 = True
                            stream_id_2 = response_data.get("streamId")
                            print(f"✅ Received playStream.start (second bot response) with streamId: {stream_id_2}")

                    elif msg_type == "playStream.chunk":
                        if stream_stopped:
                            if not play_stream_chunks_received_2:
                                print(f"✅ Started receiving playStream.chunk messages (second bot response)")
                                play_stream_chunks_received_2 = True
                            chunk_count_2 += 1

                            # Record the audio chunk
                            audio_chunk = response_data.get("audioChunk")
                            if audio_chunk:
                                recorder.record_bot_audio(audio_chunk)

                            if chunk_count_2 % 10 == 0:
                                print(f"   Received {chunk_count_2} audio chunks so far (second bot response)...")

                    elif msg_type == "playStream.stop":
                        if stream_stopped and play_stream_chunks_received_2:
                            print(f"✅ Received playStream.stop (second bot response) for streamId: {response_data.get('streamId')}")
                            second_response_complete = True
                            print(f"   Second bot response complete - received {chunk_count_2} audio chunks")
                            break

                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    print("❌ Connection closed while processing second response")
                    recorder.close()
                    return False

            if not stream_started:
                print("❌ ERROR: userStream.started was not received within timeout")
                recorder.close()
                return False

            if not stream_stopped:
                print("❌ ERROR: userStream.stopped was not received within timeout")
                recorder.close()
                return False

            if not play_stream_started_2:
                print("❌ ERROR: playStream.start (second bot response) was not received within timeout")
                recorder.close()
                return False

            if not play_stream_chunks_received_2:
                print("❌ ERROR: No playStream.chunk messages were received (second bot response)")
                recorder.close()
                return False

            print("✅ Validation completed successfully. Closing session.")
            # End the session gracefully
            try:
                session_end = {
                    "type": "session.end",
                    "conversationId": conversation_id,
                    "reasonCode": "normal",
                    "reason": "Validation completed",
                }
                await ws.send(json.dumps(session_end))
                print("✅ Sent session.end event")
                await asyncio.sleep(1)
            except websockets.exceptions.ConnectionClosed:
                print("❌ Connection closed before ending session")

            # Close the recorder and save all audio files
            recorder.close()
            return True  # All validations passed

    except ConnectionRefusedError:
        print("❌ Connection refused. Is the server running?")
        return False
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ Connection closed unexpectedly: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        return False
