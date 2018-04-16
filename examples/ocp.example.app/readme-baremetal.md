To enable full baremetal support, define the following variables when
calling the `ravello-provision-app` role:

```
publish_optimization: performance
publish_region: us-east-5
```

The following parameters must be defined per-instance:

```
prefer_physical: true
allow_nested: true
```
