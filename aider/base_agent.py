from .coders import Coder


class BaseAgent:
    def __init__(self, coder, args, analytics):
        self.coder = coder
        self.coder.agent = self
        self.args = args
        self.analytics = analytics
        self.io = coder.io
        self.next_coder_kwargs = None

    def run_interactive_loop(self):
        try:
            while True:
                try:
                    if not self.io.placeholder:
                        self.coder.copy_context()
                    user_message = self.coder.get_input()
                    self.coder.run_one(user_message, preproc=True)
                    if self.next_coder_kwargs:
                        kwargs = self.next_coder_kwargs
                        self.next_coder_kwargs = None
                        return kwargs
                    self.coder.show_undo_hint()
                except KeyboardInterrupt:
                    self.coder.keyboard_interrupt()
        except EOFError:
            self.analytics.event("exit", reason="EOF")
            return

    def schedule_switch_coder(self, **kwargs):
        self.next_coder_kwargs = kwargs

    def run(self):
        while True:
            self.coder.ok_to_warm_cache = bool(self.args.cache_keepalive_pings)
            switch_kwargs = self.run_interactive_loop()

            if not switch_kwargs:
                self.analytics.event("exit", reason="Completed main CLI coder.run")
                return

            self.coder.ok_to_warm_cache = False

            # Set the placeholder if provided
            if "placeholder" in switch_kwargs and switch_kwargs["placeholder"] is not None:
                self.io.placeholder = switch_kwargs["placeholder"]

            kwargs = dict(io=self.io, from_coder=self.coder)
            kwargs.update(switch_kwargs)
            if "show_announcements" in kwargs:
                del kwargs["show_announcements"]

            self.coder = Coder.create(agent=self, **kwargs)

            if switch_kwargs.get("show_announcements") is not False:
                self.coder.show_announcements()
