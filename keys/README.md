Generate before the event (see PREP_GUIDE.md §3):
  openssl genpkey -algorithm ed25519 -out release-signing.pem   # -> repo secret SIGNING_KEY, never commit
  openssl pkey -in release-signing.pem -pubout -out release-signing.pub   # -> commit + copy to each Pi
