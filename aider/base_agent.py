from .commands import SwitchCoder
from .coders import Coder


class BaseAgent:
    def __init__(self, coder, args, analytics):
        self.coder = coder
        self.args = args
        self.analytics = analytics
        self.io = coder.io

    def run_interactive_loop(self):
        try:
            while True:
                try:
                    if not self.io.placeholder:
                        self.coder.copy_context()
                    user_message = self.coder.get_input()
                    res = self.coder.run_one(user_message, preproc=True)
                    if isinstance(res, SwitchCoder):
                        return res
                    self.coder.show_undo_hint()
                except KeyboardInterrupt:
                    self.coder.keyboard_interrupt()
        except EOFError:
            self.analytics.event("exit", reason="EOF")
            return

    def run(self):
        while True:
            self.coder.ok_to_warm_cache = bool(self.args.cache_keepalive_pings)
            switch = self.run_interactive_loop()

            if not switch:
                self.analytics.event("exit", reason="Completed main CLI coder.run")
                return

            self.coder.ok_to_warm_cache = False

            # Set the placeholder if provided
            if hasattr(switch, "placeholder") and switch.placeholder is not None:
                self.io.placeholder = switch.placeholder

            kwargs = dict(io=self.io, from_coder=self.coder)
            kwargs.update(switch.kwargs)
            if "show_announcements" in kwargs:
                del kwargs["show_announcements"]

            self.coder = Coder.create(**kwargs)

            if switch.kwargs.get("show_announcements") is not False:
                self.coder.show_announcements()
