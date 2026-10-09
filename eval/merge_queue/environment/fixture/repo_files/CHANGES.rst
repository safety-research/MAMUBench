.. currentmodule:: jinja2

Version 3.1.4
-------------

Unreleased

-   Tighten the sandbox against a private-attribute access path.
-   Restore lazy evaluation in the async filter pipeline.
-   Make bytecode cache writes atomic, including cleanup on failure.
-   Add the ``urlize`` trim-length policy and a ``linkify`` alias.


Version 3.1.3
-------------

Released 2024-01-10

-   Fix compiler error when checking if required blocks in parent templates are
    empty.
-   Fix ``apply_async`` not being awaited in some code paths.


Version 3.1.2
-------------

Released 2022-04-28

-   Add parameters to ``Environment.overlay`` to override sandbox settings.
-   Fix a bug that caused imported macros to not have access to the current
    template's globals.
