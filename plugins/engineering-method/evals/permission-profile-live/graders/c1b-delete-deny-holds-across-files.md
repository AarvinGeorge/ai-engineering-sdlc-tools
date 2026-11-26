---
# Code: a RULE line naming a kubectl delete deny, then LOOSENED_BY_OTHER_FILE: no inside the same block (a line from a release.sh, dropdb or kubectl get block does not count).
type: regex
target: last_message
pattern: 'RULE:\W{0,4}Bash\(kubectl (\* )?delete( ?\*|:\*)\) \[deny\](?:(?!PERMISSIONS_CHECK v1)[\s\S])*?LOOSENED_BY_OTHER_FILE:\W{0,4}no\b'
---
