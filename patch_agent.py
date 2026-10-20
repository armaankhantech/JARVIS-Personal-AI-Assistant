from pathlib import Path
p = Path('agent.py')
s = p.read_text(encoding='utf-8')
imports = '''\nfrom tools.chrome_bridge import (\n    bridge_status, chrome_tabs, chrome_active_tab, chrome_navigate,\n    chrome_click, chrome_fill, chrome_press, chrome_read,\n    chrome_find_click, chrome_video_seek,\n)\n'''
if 'from tools.chrome_bridge import (' not in s:
    anchor = 'from tools.executor import ToolExecutor'
    if anchor not in s: raise SystemExit('Could not find import anchor; agent.py unchanged.')
    s = s.replace(anchor, anchor + imports, 1)
regs = '''        # Existing Chrome profile bridge (Work/Main/n8n)\n        self.registry.register("chrome_bridge_status", bridge_status, "Check the local Chrome bridge")\n        self.registry.register("chrome_tabs", chrome_tabs, "List tabs in a selected Chrome profile; profile=work/main/n8n")\n        self.registry.register("chrome_active_tab", chrome_active_tab, "Inspect the active tab; profile=work/main/n8n")\n        self.registry.register("chrome_navigate", chrome_navigate, "Navigate the active tab; arguments: url and profile")\n        self.registry.register("chrome_click", chrome_click, "Click a CSS selector in the active tab; selector and profile")\n        self.registry.register("chrome_fill", chrome_fill, "Fill a CSS selector in the active tab; selector, text, profile")\n        self.registry.register("chrome_press", chrome_press, "Press a key in a page element; key, selector, profile")\n        self.registry.register("chrome_read", chrome_read, "Read visible page text; selector and profile")\n        self.registry.register("chrome_find_click", chrome_find_click, "Click a visible link/button by text; text and profile")\n        self.registry.register("chrome_video_seek", chrome_video_seek, "Seek the current page video; seconds and profile")\n\n'''
if 'self.registry.register("chrome_bridge_status"' not in s:
    anchor = '        self.executor = ToolExecutor(self.registry)'
    if anchor not in s: raise SystemExit('Could not find tool registration anchor; agent.py unchanged.')
    s = s.replace(anchor, regs + anchor, 1)
prompt_tools = '''- chrome_bridge_status: {}\n- chrome_tabs: {"profile":"main"}\n- chrome_active_tab: {"profile":"main"}\n- chrome_navigate: {"url":"https://example.com","profile":"main"}\n- chrome_click: {"selector":"button","profile":"main"}\n- chrome_fill: {"selector":"input[name=q]","text":"hello","profile":"main"}\n- chrome_press: {"key":"Enter","selector":"input[name=q]","profile":"main"}\n- chrome_read: {"selector":"body","profile":"main"}\n- chrome_find_click: {"text":"Sign in","profile":"main"}\n- chrome_video_seek: {"seconds":30,"profile":"main"}\n'''
if '- chrome_bridge_status:' not in s:
    anchor = '- browser_play_first_youtube_result: {"query":"Python roadmap","skip_seconds":30}\n'
    if anchor not in s: raise SystemExit('Could not find PLAYWRIGHT prompt anchor; imports/registrations may have been added. Review agent.py manually.')
    s = s.replace(anchor, anchor + prompt_tools, 1)
rule = '16. For controlling the user\'s existing Work/Main/n8n Chrome windows, use chrome_* tools and pass the requested profile. Playwright browser_* tools control a separate Jarvis browser. Verify actual tool results before claiming success.\n'
if 'use chrome_* tools' not in s:
    anchor = '15. For a request to search YouTube, open the first result, and skip forward, use browser_play_first_youtube_result as a single workflow. Do not claim success unless its tool result has success=true.\n'
    if anchor not in s: raise SystemExit('Could not find system prompt rule anchor; inspect agent.py manually.')
    s = s.replace(anchor, anchor + rule, 1)
p.write_text(s, encoding='utf-8')
print('agent.py patched. Existing code preserved; Chrome bridge tools added.')
