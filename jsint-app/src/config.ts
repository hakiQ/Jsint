export const CONFIG = {
  SCANS_LIST_FEATURE_FLAG: false,
  // Base URL of this repository, e.g. "https://your-git-host/your-org/jsint".
  // Drives the in-app Repository / Support links; when unset they stay hidden
  // instead of pointing at another project's tracker.
  REPO_URL: (import.meta.env.VITE_REPO_URL as string | undefined) ?? ''
}
