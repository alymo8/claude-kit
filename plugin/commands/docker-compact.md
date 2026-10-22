---
description: Reclaim unused space in Docker Desktop's virtual disk on Windows (asks first; stops Docker; one UAC prompt)
disable-model-invocation: true
---

Give back the unused space inside Docker Desktop's virtual disk (the
`.vhdx` file) on Windows. If this is not a Windows system, say the command
does not apply and stop. Run every command below in PowerShell.

## Steps

1. Run `python "${CLAUDE_PLUGIN_ROOT}/scripts/docker-disk.py"` (fallback:
   `python ~/.claude/skills/claude-kit/scripts/docker-disk.py`) and show the
   line it prints.
   - If the line says `skipped`, report it and stop: there is nothing to
     compact.
   - If the verdict lacks `compact suggested`, say so (when it shows
     `used ?`, say the `docker-desktop` distro was not running, so used space
     is unknown), then go on to step 2: the user decides.
   - Run the script again with `--path` and keep the printed disk path.
   - If the disk path has a character outside ASCII, stop now, before
     anything is stopped, and tell the user to run diskpart by hand with the
     four lines under step 6 (diskpart reads the script as ASCII).
2. **Ask the user before anything else.** Compacting stops Docker Desktop and
   every container, and needs one UAC prompt. Wait for a clear yes. A no ends
   the command with nothing changed.
3. If the distro is running (`wsl -l --running -q` lists `docker-desktop`),
   run `wsl -d docker-desktop -- fstrim -v /mnt/docker-desktop-disk`. Report a
   failure and continue.
4. Ask the user to quit Docker Desktop from its tray icon and confirm. Then
   run `wsl --shutdown`.
5. If the line said `not sparse`, ask a separate yes/no question. On yes, run
   `wsl --manage docker-desktop --set-sparse true`.
6. Create the folder `%TEMP%\dcompact`
   (`New-Item -ItemType Directory -Force "$env:TEMP\dcompact"`) and write
   `compact.txt` in it with `Set-Content -Encoding ascii` (ASCII, no BOM),
   with these lines:
   ```
   select vdisk file="<disk path>"
   attach vdisk readonly
   compact vdisk
   detach vdisk
   ```
   The path is short and fixed on purpose: writing under the session
   scratchpad failed on a long-path error on 2026-10-21, and a fixed path
   avoids quoting problems with diskpart's `/s`.
7. Note the file size with `(Get-Item <disk path>).Length`. Then, in one
   PowerShell call, run:
   ```
   try { $p = Start-Process diskpart -ArgumentList "/s `"$env:TEMP\dcompact\compact.txt`"" -Verb RunAs -Wait -PassThru -ErrorAction Stop; $p.ExitCode } catch { 'declined' }
   ```
   The single quoted `-ArgumentList` string keeps a `%TEMP%` path with a
   space in one piece (Windows PowerShell 5.1 does not quote list elements).
   A `declined` result means the UAC prompt was declined and nothing was
   compacted. `ExitCode` 0 is success; any other code, or an empty result, is
   a failure.
8. Run `Remove-Item -Recurse -Force "$env:TEMP\dcompact"`, whether or not
   diskpart succeeded.
9. Report the outcome from step 7 and the file size before and after, in GiB.
   Tell the user to start Docker Desktop again, then run the status script
   once more for the full line.

## Rule

The command never removes Docker objects, never touches volumes, and never
empties anything. Compaction only gives back unused blocks of the disk file.
