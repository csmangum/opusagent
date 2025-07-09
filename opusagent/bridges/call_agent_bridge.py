from opusagent.bridges.audiocodes_bridge import AudioCodesBridge
from opusagent.config.logging_config import configure_logging

logger = configure_logging("call_agent_bridge")


class CallAgentBridge(AudioCodesBridge):
    """Caller-side bridge for intelligent caller agents.

    This bridge allows an *outgoing* caller (e.g. created by ``caller_agent.CallAgent``)
    to connect to the same OpenAI Realtime back-end as the inbound bridges
    (``AudioCodesBridge`` / ``TwilioBridge``).

    It intentionally re-uses the AudioCodes VAIC message structure (``session.*``,
    ``userStream.*``, ``playStream.*``), because the existing
    :class:`validate.mock_audiocodes_client.MockAudioCodesClient` already speaks that
    dialect.  By subclassing :class:`~opusagent.bridges.audiocodes_bridge.AudioCodesBridge`
    we inherit all of the necessary plumbing: event routing, audio handling and
    response generation.

    At the moment this class does not add new behaviour; it mainly exists to
    provide:

    1.  Semantic clarity in the codebase – we can clearly differentiate between
        *inbound* (customer side) bridges and the *caller* side bridge used for
        synthetic testing or outbound dialling.
    2.  A dedicated logger namespace (``call_agent_bridge``) so that caller-side
        traffic can be filtered separately from real customer traffic.

    Future enhancements (e.g. caller-specific metrics, alternative event
    formats, authentication etc.) can be implemented here without impacting the
    AudioCodes / Twilio bridges.
    """

    def __init__(self, platform_websocket, realtime_websocket, session_config):
        """Initialize the caller-side bridge.

        Besides the standard AudioCodes behaviour we also need to make sure the
        *caller* specific function set (``hang_up`` etc.) is registered with the
        :class:`~opusagent.function_handler.FunctionHandler`.  The
        :class:`~opusagent.bridges.base_bridge.BaseRealtimeBridge` base class
        automatically registers the **customer-service** functions which are
        useful for the agent that answers the phone, but for the synthetic
        caller we want its own tools instead.
        """

        # Call parent constructor first (this wires up audio / event routing)
        super().__init__(platform_websocket, realtime_websocket, session_config)

        # Register the caller-side functions (e.g. ``hang_up``)
        #! Make function registration be outside of the class
        try:
            from opusagent.caller_agent import register_caller_functions

            register_caller_functions(self.function_handler)
            logger.info("Caller functions registered with function handler")
        except Exception as e:
            logger.error(f"Failed to register caller functions: {e}")

        # Optionally, we could unregister customer-service functions here to
        # avoid name collisions.  Right now there are no overlapping names so
        # we leave them in place.

    # NOTE:  No further implementation is required right now – message routing
    #        and audio streaming are inherited from AudioCodesBridge.
