/**
 * Cluster tools for seats on the shared inference cluster.
 *
 * The tool list (names, descriptions, JSON-schema parameters) comes from `tools.json` in the agent dir;
 * each call goes to the cluster controller, authenticated by the session token in this process's
 * environment.
 */

import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

interface ToolSpec {
	name: string;
	description: string;
	parameters: Record<string, unknown>;
}

const UNREACHABLE = "error: the cluster controller is not responding; try again shortly.";

function loadTools(): ToolSpec[] {
	// The runner materializes tools.json in the seat's own default agent dir; prefer that, with the
	// (ambient, version-dependent) PI_CODING_AGENT_DIR only as a fallback. pi 0.77.0 does not export
	// the env var to extensions at all. A missing manifest is a deployment bug — FAIL LOUD: a silent
	// empty toolset once shipped whole "clean" episodes of toolless seats.
	const candidates = [
		path.join(os.homedir(), ".pi", "agent", "tools.json"),
		...(process.env.PI_CODING_AGENT_DIR ? [path.join(process.env.PI_CODING_AGENT_DIR, "tools.json")] : []),
	];
	for (const toolsPath of candidates) {
		if (fs.existsSync(toolsPath)) return JSON.parse(fs.readFileSync(toolsPath, "utf-8")) as ToolSpec[];
	}
	throw new Error(`labctl extension: tools.json not found (looked in: ${candidates.join(", ")})`);
}

async function callController(command: string, args: Record<string, unknown>, signal: AbortSignal): Promise<string> {
	const base = process.env.LABCTL_SERVER;
	const token = process.env.LABCTL_TOKEN;
	if (!base || !token) return "error: no cluster session configured.";
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

export default function (pi: ExtensionAPI) {
	for (const tool of loadTools()) {
		pi.registerTool({
			name: tool.name,
			label: tool.name,
			description: tool.description,
			parameters: tool.parameters as never,
			async execute(_toolCallId, params, signal) {
				const text = await callController(tool.name, (params ?? {}) as Record<string, unknown>, signal);
				return { content: [{ type: "text", text }] };
			},
		});
	}
}
