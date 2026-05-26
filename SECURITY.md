# Security Policy

## Supported versions

`agentcore` is pre-alpha (0.0.x). Only `main` receives security updates. There are no LTS branches, no backport policy, and no commitments around API stability.

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

If you find a security issue, please email the maintainers privately:

- Use GitHub's [private security advisory](https://github.com/bencrooks-dev/agentcore/security/advisories/new) feature
- Or open an issue titled "SECURITY — please contact me privately" with no details, and we will reach out

Please include:

1. A description of the issue and the affected component
2. Steps to reproduce, or a proof-of-concept
3. The version (`pip show agentcore`) or commit SHA
4. Your environment (OS, Python version, threading model)
5. Any mitigations you've already identified

## Response timeline

We aim to:

- Acknowledge receipt within **3 business days**
- Provide an initial assessment within **7 business days**
- Coordinate a fix with you before public disclosure

This is a best-effort commitment from volunteer maintainers, not an SLA.

## Threat model — what is in and out of scope

`agentcore` is a library, not a service. We treat the following as in scope:

- Memory corruption in the C++ core (use-after-free, buffer overrun, race conditions producing UB)
- GIL safety violations in Pybind11 bindings
- Code execution via crafted tool arguments or messages
- Denial of service via the public Python API with reasonable inputs
- Secrets leakage from provider implementations (e.g. API keys in error messages)

Out of scope:

- Vulnerabilities in optional dependencies (`openai`, `anthropic`, `httpx`) — please report those upstream
- Misuse: registering an obviously dangerous tool body (`subprocess.run`) and then complaining when it runs
- Side-channel attacks against the LLM provider itself (prompt injection, jailbreaking) — these are LLM concerns, not library concerns
- Insecure defaults in user code that imports `agentcore`

## Known security-relevant limitations

These are documented limitations as of `main`. They are not vulnerabilities in their own right — they are constraints the user should be aware of when designing systems on top of `agentcore`:

1. **Tool arguments are not validated against the registered schema.** The schema is informational only. Tool bodies must validate their own inputs.
2. **No message size cap.** A caller passing an unbounded `Message.content` could OOM the process.
3. **No request timeout in the `Provider` interface.** Provider implementations may hang indefinitely on a stuck network call.
4. **`AgentRouter` inboxes are unbounded.** A producer with no consumer will grow memory without backpressure.
5. **No cancellation tokens.** Once `generate` or `invoke` starts, there is no in-process way to stop it.

Production users should layer their own validation, timeouts, and backpressure on top until these land natively.

## Public disclosure

Once a fix is released, we will:

- Publish a GitHub Security Advisory describing the issue, affected versions, and fix
- Credit the reporter (with your permission)
- Coordinate any CVE assignment if appropriate
