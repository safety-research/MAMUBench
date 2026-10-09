/**
 * Assistant-console tools for personal-assistant seats on the shared hub.
 *
 * The tool list (names, descriptions, JSON-schema parameters) comes from `tools.json` in the agent
 * dir; each call goes to the assistant hub, authenticated by the session token in this process's
 * environment. At session start the seat also attests its runtime surface to the hub: the active
 * tools, the thinking level, and every `<project_instructions>` block pi appended to its system
 * prompt (pi's context-file channel: the seat's cwd AGENTS.md when the seat is launched without
 * `--no-context-files`, nothing when it is launched with it), each as its path plus the sha256 of
 * its verbatim body. The hub's preflight compares that list against what it staged, so a seat
 * whose prompt carries the wrong file, an extra file, or none when one is expected fails closed
 * before any prompt is sent.
 */

import { createHash } from "node:crypto";
import * as fs from "node:fs";
import * as path from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

interface ToolSpec {
	name: string;
	description: string;
	parameters: Record<string, unknown>;
}

interface ProjectContextBlock {
	path: string;
	sha256: string;
}

const UNREACHABLE = "error: the assistant hub is not responding; try again shortly.";

function loadTools(): ToolSpec[] {
	const agentDir = process.env.PI_CODING_AGENT_DIR;
	if (!agentDir) return [];
	const toolsPath = path.join(agentDir, "tools.json");
	if (!fs.existsSync(toolsPath)) return [];
	return JSON.parse(fs.readFileSync(toolsPath, "utf-8")) as ToolSpec[];
}

/** Every `<project_instructions path="...">` block pi built into the system prompt, body hashed verbatim. */
function projectContextBlocks(systemPrompt: string): ProjectContextBlock[] {
	const blocks: ProjectContextBlock[] = [];
	const pattern = /<project_instructions path="([^"]*)">\n([\s\S]*?)\n<\/project_instructions>/g;
	for (const match of systemPrompt.matchAll(pattern)) {
		blocks.push({ path: match[1], sha256: createHash("sha256").update(match[2], "utf8").digest("hex") });
	}
	return blocks;
}

async function callHub(command: string, args: Record<string, unknown>, signal: AbortSignal): Promise<string> {
	const base = process.env.PA_HUB_SERVER;
	const token = process.env.PA_HUB_TOKEN;
	if (!base || !token) return "error: no assistant-hub session configured.";
	const timeout = AbortSignal.timeout(60_000);
	const merged = AbortSignal.any ? AbortSignal.any([signal, timeout]) : timeout;
	try {
		const resp = await fetch(`${base}/agent/call`, {
			method: "POST",
			headers: { "Content-Type": "application/json", "X-Seat-Token": token },
			body: JSON.stringify({ command, args }),
			signal: merged,
		});
		const payload = (await resp.json()) as { text?: string };
		return payload.text ?? UNREACHABLE;
	} catch {
		return UNREACHABLE;
	}
}

async function attestRuntime(pi: ExtensionAPI, ctx: ExtensionContext): Promise<void> {
	const base = process.env.PA_HUB_SERVER;
	const token = process.env.PA_HUB_TOKEN;
	if (!base || !token) return;
	const response = await fetch(`${base}/runtime/attest`, {
		method: "POST",
		headers: { "Content-Type": "application/json", "X-Seat-Token": token },
		body: JSON.stringify({
			active_tools: pi.getActiveTools(),
			all_tools: pi.getAllTools().map((tool) => tool.name),
			thinking: pi.getThinkingLevel(),
			project_context: projectContextBlocks(ctx.getSystemPrompt()),
		}),
	});
	if (!response.ok) throw new Error(`runtime attestation failed: HTTP ${response.status}`);
}

export default function (pi: ExtensionAPI) {
	for (const tool of loadTools()) {
		pi.registerTool({
			name: tool.name,
			label: tool.name,
			description: tool.description,
			parameters: tool.parameters as never,
			async execute(_toolCallId, params, signal) {
				const text = await callHub(tool.name, (params ?? {}) as Record<string, unknown>, signal);
				return { content: [{ type: "text", text }] };
			},
		});
	}
	pi.on("session_start", async (_event, ctx) => {
		await attestRuntime(pi, ctx);
	});
}
