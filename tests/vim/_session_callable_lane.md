## TOAS:USER

```yaml
- operation: shell_script
  arguments:
    script: |
      i=1
      while [ $i -le 12 ]; do
        echo tick-c-$i
        sleep 0.15
        i=$((i+1))
      done
```
