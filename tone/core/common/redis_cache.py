import json
import pickle
import time
import uuid

import redis
from django.conf import settings


class RedisControl(object):
    def __init__(self, cache_db=None):
        if settings.REDIS_CACHE_SWITCH:
            if not cache_db:
                cache_db = settings.REDIS_CACHE_DB
            self.pool = redis.ConnectionPool(
                host=settings.REDIS_HOST,
                port=int(settings.REDIS_PORT),
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                db=int(cache_db)
            )
            self.cursor = redis.Redis(connection_pool=self.pool)

    def get_info(self, key):
        return self.cursor.get(key)

    def set_info(self, name, value, ex=None, px=None, nx=False, xx=False):
        return self.cursor.set(name=name, value=value, ex=ex, px=px, nx=nx, xx=xx)

    def hset(self, name, key, value):
        return self.cursor.hset(name, key, value)

    def hmset(self, name, mapping):
        return self.cursor.hmset(name, mapping)

    def hsetnx(self, name, key, value):
        return self.cursor.hsetnx(name, key, value)

    def hget(self, name, key):
        return self.cursor.hget(name, key)

    def hmget(self, name, *keys):
        return self.cursor.hmget(name, keys)

    def hgetall(self, name):
        return self.cursor.hgetall(name)

    def hexists(self, name, key):
        return self.cursor.hexists(name, key)

    def hlen(self, name):
        return self.cursor.hlen(name)

    def hdel(self, name, *keys):
        return self.cursor.hdel(name, *keys)

    def expire(self, name, timeout):
        self.cursor.expire(name, timeout)

    def delete(self, *name):
        self.cursor.delete(*name)

    def setnx(self, name, timeout):
        return self.cursor.setnx(name, timeout)

    def exists(self, name):
        return self.cursor.exists(name)

    def delete_like(self, name):
        keys = self.cursor.keys(name)
        if keys:
            return self.cursor.delete(*keys)
        return None

    def sadd(self, name, *value):
        return self.cursor.sadd(name, *value)

    def sismember(self, name, value):
        return self.cursor.sismember(name, value)

    def zrank(self, name, value):
        return self.cursor.zrank(name, value)

    def zadd(self, name, args, *kwargs):
        return self.cursor.zadd(name, args, *kwargs)

    def zrem(self, name, *values):
        return self.cursor.zrem(name, *values)

    def lpush(self, name, *values):
        return self.cursor.lpush(name, *values)

    def rpop(self, name):
        return self.cursor.rpop(name)

    def scard(self, name):
        return self.cursor.scard(name)

    def srem(self, name, *values):
        return self.cursor.srem(name, *values)

    def llen(self, name):
        return self.cursor.llen(name)

    def lrem(self, name, count, value):
        return self.cursor.lrem(name, count, value)

    def keys(self, pattern):
        return self.cursor.keys(pattern)

    def smembers(self, name):
        return self.cursor.smembers(name)

    def lrange(self, name, start, end):
        return self.cursor.lrange(name, start, end)


class RedisCache(RedisControl):
    def __init__(self, cache_db=None, key_perfix="tone-"):
        self.key_perfix = key_perfix
        if settings.REDIS_CACHE_SWITCH:
            if cache_db is None:
                cache_db = settings.REDIS_CACHE_DB
            self.pool = redis.ConnectionPool(host=settings.REDIS_HOST, port=int(settings.REDIS_PORT),
                                             password=settings.REDIS_PASSWORD, decode_responses=True,
                                             db=int(cache_db))
            self.cursor = redis.Redis(connection_pool=self.pool, socket_timeout=10)

    def get(self, key, serialize_mode="json"):
        if not settings.REDIS_CACHE_SWITCH:
            return None, "redis cache switch is shut down"
        key = self.key_perfix + str(key)
        data = self.cursor.get(key)
        if data is None:
            return None, "Expired or nonexistent"
        if serialize_mode == "pickle":
            data = pickle.loads(data)
        elif serialize_mode == "json":
            data = json.loads(data)
        return True, data

    def set(self, key, value, expired=None, nx=True, serialize_mode="json"):
        if not settings.REDIS_CACHE_SWITCH:
            return None
        key = self.key_perfix + str(key)
        if serialize_mode == "pickle":
            value = pickle.dumps(value)
        elif serialize_mode == "json":
            value = json.dumps(value)
        elif serialize_mode == "string":
            value = str(value)
        return self.cursor.set(key, value, ex=expired, nx=nx)

    def acquire_lock(self, lock_name, acquire_time=10, time_out=60):
        """获取一个分布式锁"""
        identifier = str(uuid.uuid4())
        end = time.time() + acquire_time
        lock = "string:lock:" + lock_name
        while time.time() < end:
            if self.set(lock, identifier, expired=time_out, nx=True):
                return identifier
            time.sleep(0.001)
        return False

    def release_lock(self, lock_name, identifier):
        """通用的锁释放函数"""
        lock = "string:lock:{}".format(lock_name)
        while True:
            try:
                lock_value = self.get(lock)
                if not lock_value[0]:
                    return True

                if lock_value[1] == identifier:
                    lock = "{}string:lock:{}".format(self.key_perfix, lock_name)
                    self.delete(lock)
                    return True
                break
            except redis.WatchError:
                pass
        return False


redis_cache = RedisCache()

runner_redis_cache = RedisCache(cache_db=settings.RUNNER_REDIS_CACHE_DB, key_perfix="")
