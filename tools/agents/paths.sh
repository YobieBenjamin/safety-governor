# Where the clones live. Sourced by every script under tools/; setup_and_publish.sh carries the
# same three lines itself, because it runs before any clone exists.
#
# The four repositories (safety-governor, safety, hardware-and-silicon, Watermark) sit beside each
# other in one directory. On the Mac mini that is the external drive, /Volumes/External_4TB/Safety
# Experiments, whenever it is mounted; anywhere else it is $HOME. PROJECT_WORK overrides both.
# After the move, ~/<repo> stays behind as a symlink to the moved clone, so an old command still
# lands in the right place. GitHub (github.com/YobieBenjamin) is the source of truth either way.
WORK="${PROJECT_WORK:-}"
if [ -z "$WORK" ]; then
  if [ -d "/Volumes/External_4TB/Safety Experiments" ]; then WORK="/Volumes/External_4TB/Safety Experiments"; else WORK="$HOME"; fi
fi
INBOX="$WORK/inbox"   # bundles made in the program's container land here (setup_and_publish.sh also looks beside itself)
