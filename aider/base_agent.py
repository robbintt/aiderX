from aider import urls
from .coders import Coder
from .coders.base_coder import UnknownEditFormat


class BaseAgent:
    def __init__(self, args, analytics, io):
        self.coder = None
        self.args = args
        self.analytics = analytics
        self.io = io
        self.next_coder_kwargs = None

    def create_coder(
        self,
        main_model,
        repo,
        fnames,
        read_only_fnames,
        lint_cmds,
        commands,
        summarizer,
    ):
        if self.args.map_tokens is None:
            map_tokens = main_model.get_repo_map_tokens()
        else:
            map_tokens = self.args.map_tokens

        # Track auto-commits configuration
        self.analytics.event("auto_commits", enabled=bool(self.args.auto_commits))

        coder = Coder.create(
            main_model=main_model,
            edit_format=self.args.edit_format,
            io=self.io,
            repo=repo,
            fnames=fnames,
            read_only_fnames=read_only_fnames,
            show_diffs=self.args.show_diffs,
            auto_commits=self.args.auto_commits,
            dirty_commits=self.args.dirty_commits,
            dry_run=self.args.dry_run,
            map_tokens=map_tokens,
            verbose=self.args.verbose,
            stream=self.args.stream,
            use_git=self.args.git,
            restore_chat_history=self.args.restore_chat_history,
            auto_lint=self.args.auto_lint,
            auto_test=self.args.auto_test,
            lint_cmds=lint_cmds,
            test_cmd=self.args.test_cmd,
            commands=commands,
            summarizer=summarizer,
            analytics=self.analytics,
            map_refresh=self.args.map_refresh,
            cache_prompts=self.args.cache_prompts,
            map_mul_no_files=self.args.map_multiplier_no_files,
            num_cache_warming_pings=self.args.cache_keepalive_pings,
            suggest_shell_commands=self.args.suggest_shell_commands,
            chat_language=self.args.chat_language,
            commit_language=self.args.commit_language,
            detect_urls=self.args.detect_urls,
            auto_copy_context=self.args.copy_paste,
            auto_accept_architect=self.args.auto_accept_architect,
            add_gitignore_files=self.args.add_gitignore_files,
            llm_command=self.args.llm_command,
            handlers=self.args.handlers,
        )
        return coder

    def setup_coder(
        self, main_model, repo, fnames, read_only_fnames, lint_cmds, commands, summarizer
    ):
        try:
            self.coder = self.create_coder(
                main_model,
                repo,
                fnames,
                read_only_fnames,
                lint_cmds,
                commands,
                summarizer,
            )
        except UnknownEditFormat as err:
            self.io.tool_error(str(err))
            self.io.offer_url(urls.edit_formats, "Open documentation about edit formats?")
            self.analytics.event("exit", reason="Unknown edit format")
            return None
        except ValueError as err:
            self.io.tool_error(str(err))
            self.analytics.event("exit", reason="ValueError during coder creation")
            return None

        self.coder.agent = self
        return self.coder

    def run_interactive_loop(self):
        try:
            while True:
                try:
                    if not self.io.placeholder:
                        self.coder.copy_context()
                    user_message = self.get_input()
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

    def get_input(self):
        inchat_files = self.coder.get_inchat_relative_files()
        read_only_files = [
            self.coder.get_rel_fname(fname) for fname in self.coder.abs_read_only_fnames
        ]
        all_files = sorted(set(inchat_files + read_only_files))
        edit_format = (
            "" if self.coder.edit_format == self.coder.main_model.edit_format else self.coder.edit_format
        )
        return self.io.get_input(
            self.coder.root,
            all_files,
            self.coder.get_addable_relative_files(),
            self.coder.commands,
            self.coder.abs_read_only_fnames,
            edit_format=edit_format,
        )

    def schedule_switch_coder(self, **kwargs):
        self.next_coder_kwargs = kwargs

    def run(self, with_message=None):
        if with_message:
            self.coder.run(with_message=with_message)
            return

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
