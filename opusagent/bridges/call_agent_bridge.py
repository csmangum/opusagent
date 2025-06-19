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

    # NOTE:  No additional implementation is required right now because all the
    #        AudioCodes message semantics are sufficient for the caller side as
    #        well.  The class is defined explicitly so that we can wire it up in
    #        ``main.handle_caller_call`` and keep the log namespaces clean.

    pass 