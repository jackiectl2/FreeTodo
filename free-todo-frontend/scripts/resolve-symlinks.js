/**
 * Materialize only the package links at the root of a Next.js standalone
 * node_modules directory. Never recurse into pnpm's content-addressed store:
 * doing so expands the complete dependency graph and may follow links back to
 * a developer checkout.
 */

const fs = require("node:fs");
const path = require("node:path");

function isInside(parent, child) {
	const relative = path.relative(parent, child);
	return relative === "" || (!relative.startsWith(`..${path.sep}`) && relative !== "..");
}

function resolvePackageLinks(dir, standaloneNodeModules) {
	const entries = fs.readdirSync(dir, { withFileTypes: true });

	for (const entry of entries) {
		if (entry.name === ".pnpm") {
			continue;
		}
		const fullPath = path.join(dir, entry.name);

		if (entry.isSymbolicLink()) {
			try {
				const target = fs.readlinkSync(fullPath);
				const resolvedPath = path.isAbsolute(target)
					? target
					: path.resolve(path.dirname(fullPath), target);

				if (!isInside(standaloneNodeModules, resolvedPath)) {
					throw new Error(
						`refusing to follow a link outside standalone node_modules: ${resolvedPath}`,
					);
				}

				if (fs.existsSync(resolvedPath)) {
					// 删除符号链接
					fs.unlinkSync(fullPath);

					// 如果是目录，复制整个目录
					if (fs.statSync(resolvedPath).isDirectory()) {
						copyDirectory(resolvedPath, fullPath);
					} else {
						// 如果是文件，复制文件
						fs.copyFileSync(resolvedPath, fullPath);
					}

					console.log(`Resolved symlink: ${entry.name} -> ${resolvedPath}`);
				} else {
					console.warn(`Symlink target not found: ${fullPath} -> ${target}`);
				}
			} catch (error) {
				console.error(`Error resolving symlink ${fullPath}:`, error.message);
			}
		} else if (entry.isDirectory() && entry.name.startsWith("@")) {
			// Scoped packages are one directory deeper. Do not recurse into normal
			// package directories or pnpm's internal store.
			resolvePackageLinks(fullPath, standaloneNodeModules);
		}
	}
}

function copyDirectory(src, dest) {
	fs.mkdirSync(dest, { recursive: true });
	const entries = fs.readdirSync(src, { withFileTypes: true });

	for (const entry of entries) {
		const srcPath = path.join(src, entry.name);
		const destPath = path.join(dest, entry.name);

		if (entry.isSymbolicLink()) {
			const resolvedTarget = fs.realpathSync(srcPath);
			const relativeTarget = path.relative(path.dirname(destPath), resolvedTarget);
			fs.symlinkSync(
				relativeTarget,
				destPath,
				fs.statSync(resolvedTarget).isDirectory() ? "dir" : "file",
			);
		} else if (entry.isDirectory()) {
			copyDirectory(srcPath, destPath);
		} else {
			fs.copyFileSync(srcPath, destPath);
		}
	}
}

const standaloneDir = process.env.FREETODO_STANDALONE_NODE_MODULES
	? path.resolve(process.env.FREETODO_STANDALONE_NODE_MODULES)
	: path.join(__dirname, "..", ".next", "standalone", "node_modules");

if (fs.existsSync(standaloneDir)) {
	console.log("Resolving symlinks in standalone node_modules...");
	resolvePackageLinks(standaloneDir, standaloneDir);
	console.log("Symlink resolution complete!");
} else {
	console.warn(`Standalone node_modules not found at: ${standaloneDir}`);
	console.warn("Skipping symlink resolution.");
}

module.exports = { copyDirectory, isInside, resolvePackageLinks };
