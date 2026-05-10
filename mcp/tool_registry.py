from typing import Dict, List, Type
from .base_tool import BaseAgenticTool

class ToolRegistry:
    """
    Registry for all available tools in the system.
    Allows dynamic discovery and fetching of tools for agents.
    """
    _tools: Dict[str, BaseAgenticTool] = {}

    @classmethod
    def register(cls, tool: BaseAgenticTool):
        """Register an instantiated tool."""
        if tool.name in cls._tools:
            print(f"Warning: Tool '{tool.name}' is already registered. Overwriting.")
        cls._tools[tool.name] = tool

    @classmethod
    def get_tool(cls, name: str) -> BaseAgenticTool:
        """Fetch a specific tool by name."""
        if name not in cls._tools:
            raise ValueError(f"Tool '{name}' not found in registry.")
        return cls._tools[name]

    @classmethod
    def get_all_tools(cls) -> List[BaseAgenticTool]:
        """Return a list of all registered tools."""
        return list(cls._tools.values())
        
    @classmethod
    def get_langchain_tools(cls) -> List:
        """Return all registered tools as LangChain StructuredTools."""
        return [tool.to_langchain_tool() for tool in cls.get_all_tools()]

    @classmethod
    def register_core_tools(cls):
        """Registers all core tools into the registry. Call once on application startup."""
        from .tools.llm_tools.text_generator import TextGeneratorTool
        from .tools.llm_tools.json_structurer import JsonStructurerTool
        from .tools.audio_tools.tts_tool import TTSTool
        from .tools.audio_tools.bgm_tool import BGMTool
        from .tools.audio_tools.audio_merger import AudioMergerTool

        cls.register(TextGeneratorTool())
        cls.register(JsonStructurerTool())
        cls.register(TTSTool())
        cls.register(BGMTool())
        cls.register(AudioMergerTool())

    @classmethod
    def register_video_tools(cls):
        """Registers all Phase 3 video/vision tools. Requires FFmpeg in PATH."""
        from .tools.vision_tools.image_gen_tool import ImageGenTool
        from .tools.video_tools.ffmpeg_tool import FFmpegTool
        from .tools.video_tools.wan_video_tool import WanVideoTool
        from .tools.video_tools.compositor_tool import CompositorTool
        from .tools.video_tools.subtitle_tool import SubtitleTool

        cls.register(ImageGenTool())
        cls.register(FFmpegTool())
        cls.register(WanVideoTool())
        cls.register(CompositorTool())
        cls.register(SubtitleTool())
