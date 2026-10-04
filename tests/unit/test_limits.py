from packages.security.limits import TokenBucket

def test_bucket_limits_burst():
    bucket = TokenBucket(capacity=2, refill_per_second=0)
    assert bucket.allow()
    assert bucket.allow()
    assert not bucket.allow()
