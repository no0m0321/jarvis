"""수학/통계/과학 — prime, gcd/lcm, stats, combinatorics, matrix, equations."""
from __future__ import annotations

import math
import statistics
from typing import List

from jarvis.tools.registry import REGISTRY, Tool


def _prime_check(n: int) -> str:
    n = int(n)
    if n < 2:
        return f"{n}: not prime (n<2)"
    if n < 4:
        return f"{n}: prime"
    if n % 2 == 0:
        return f"{n}: composite (even)"
    for i in range(3, int(math.isqrt(n)) + 1, 2):
        if n % i == 0:
            return f"{n}: composite (={i}·{n//i})"
    return f"{n}: prime"


def _prime_factor(n: int) -> str:
    n = int(n)
    if n < 2:
        return f"{n}: no factors"
    factors = []
    x = n
    d = 2
    while d * d <= x:
        while x % d == 0:
            factors.append(d)
            x //= d
        d += 1
    if x > 1:
        factors.append(x)
    return f"{n} = " + " · ".join(map(str, factors))


def _gcd_lcm(a: int, b: int) -> str:
    g = math.gcd(int(a), int(b))
    l = abs(int(a) * int(b)) // g if g else 0
    return f"gcd({a},{b}) = {g}\nlcm({a},{b}) = {l}"


def _quadratic(a: float, b: float, c: float) -> str:
    """ax^2 + bx + c = 0."""
    if a == 0:
        if b == 0:
            return "ERROR: not a polynomial"
        return f"linear: x = {-c/b}"
    disc = b * b - 4 * a * c
    if disc > 0:
        sq = math.sqrt(disc)
        return f"two real roots:\n  x1 = {(-b + sq) / (2*a)}\n  x2 = {(-b - sq) / (2*a)}"
    if disc == 0:
        return f"one real root: x = {-b/(2*a)}"
    sq = math.sqrt(-disc)
    return f"complex roots:\n  x1 = {-b/(2*a)} + {sq/(2*a)}i\n  x2 = {-b/(2*a)} - {sq/(2*a)}i"


def _stats(values_csv: str) -> str:
    try:
        vals = [float(x) for x in values_csv.split(",") if x.strip()]
    except ValueError:
        return "ERROR: 쉼표 구분 숫자"
    if not vals:
        return "(empty)"
    s = sorted(vals)
    return (f"n: {len(vals)}\n"
            f"sum: {sum(vals):g}\n"
            f"min: {min(vals):g}\n"
            f"max: {max(vals):g}\n"
            f"mean: {statistics.mean(vals):.4f}\n"
            f"median: {statistics.median(vals):.4f}\n"
            f"stdev: {statistics.stdev(vals) if len(vals) > 1 else 0:.4f}\n"
            f"variance: {statistics.variance(vals) if len(vals) > 1 else 0:.4f}\n"
            f"p25: {s[len(s)//4]:g}\n"
            f"p75: {s[(3*len(s))//4]:g}")


def _correlation(xs_csv: str, ys_csv: str) -> str:
    """피어슨 상관계수 + 단순 선형회귀."""
    try:
        xs = [float(x) for x in xs_csv.split(",") if x.strip()]
        ys = [float(y) for y in ys_csv.split(",") if y.strip()]
    except ValueError:
        return "ERROR: 쉼표 구분 숫자"
    if len(xs) != len(ys) or len(xs) < 2:
        return "ERROR: 길이 같아야 함, n>=2"
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (len(xs) - 1)
    sx = statistics.stdev(xs)
    sy = statistics.stdev(ys)
    r = cov / (sx * sy) if sx * sy else 0
    # y = a + b*x
    b = cov / (sx * sx) if sx else 0
    a = my - b * mx
    return f"r (pearson): {r:.4f}\nlinear: y = {a:.4f} + {b:.4f}·x"


def _combinations(n: int, r: int) -> str:
    n, r = int(n), int(r)
    if n < 0 or r < 0 or r > n:
        return "ERROR: 0 ≤ r ≤ n"
    return f"C({n},{r}) = {math.comb(n, r):,}\nP({n},{r}) = {math.perm(n, r):,}"


def _matrix_2x2_invert(a: float, b: float, c: float, d: float) -> str:
    """[[a,b],[c,d]] 역행렬."""
    det = a * d - b * c
    if det == 0:
        return f"det = 0 (singular, no inverse)"
    return (f"det = {det:g}\n"
            f"inv = 1/{det:g} · [[{d:g}, {-b:g}], [{-c:g}, {a:g}]]\n"
            f"    = [[{d/det:.4f}, {-b/det:.4f}], [{-c/det:.4f}, {a/det:.4f}]]")


def _factorial(n: int) -> str:
    n = int(n)
    if n < 0:
        return "ERROR: n>=0"
    if n > 1000:
        return "ERROR: n<=1000"
    return f"{n}! = {math.factorial(n)}"


def _fibonacci(n: int) -> str:
    n = int(n)
    if n < 0 or n > 100:
        return "ERROR: 0 ≤ n ≤ 100"
    a, b = 0, 1
    seq: List[int] = []
    for _ in range(n + 1):
        seq.append(a)
        a, b = b, a + b
    return f"F({n}) = {seq[-1]}\nseq: {seq}"


def _percentile(values_csv: str, p: float) -> str:
    try:
        vals = sorted(float(x) for x in values_csv.split(",") if x.strip())
    except ValueError:
        return "ERROR"
    if not vals:
        return "(empty)"
    if p < 0 or p > 100:
        return "ERROR: 0 ≤ p ≤ 100"
    k = (len(vals) - 1) * p / 100
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return f"p{p}: {vals[int(k)]:g}"
    return f"p{p}: {vals[f] + (vals[c] - vals[f]) * (k - f):g}"


REGISTRY.register(Tool(
    name="prime_check",
    description="소수 여부 + 가장 작은 인수.",
    input_schema={"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]},
    handler=_prime_check,
))
REGISTRY.register(Tool(
    name="prime_factor",
    description="소인수분해.",
    input_schema={"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]},
    handler=_prime_factor,
))
REGISTRY.register(Tool(
    name="gcd_lcm",
    description="최대공약수/최소공배수.",
    input_schema={
        "type": "object",
        "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
        "required": ["a", "b"],
    },
    handler=_gcd_lcm,
))
REGISTRY.register(Tool(
    name="quadratic_solve",
    description="ax² + bx + c = 0 풀이 (실근/복소근).",
    input_schema={
        "type": "object",
        "properties": {"a": {"type": "number"}, "b": {"type": "number"}, "c": {"type": "number"}},
        "required": ["a", "b", "c"],
    },
    handler=_quadratic,
))
REGISTRY.register(Tool(
    name="stats_summary",
    description="기술 통계: n/sum/min/max/mean/median/stdev/p25/p75.",
    input_schema={
        "type": "object",
        "properties": {"values_csv": {"type": "string"}},
        "required": ["values_csv"],
    },
    handler=_stats,
))
REGISTRY.register(Tool(
    name="correlation",
    description="x,y 두 series의 피어슨 상관계수 + 선형회귀.",
    input_schema={
        "type": "object",
        "properties": {"xs_csv": {"type": "string"}, "ys_csv": {"type": "string"}},
        "required": ["xs_csv", "ys_csv"],
    },
    handler=_correlation,
))
REGISTRY.register(Tool(
    name="combinations_permutations",
    description="C(n,r) + P(n,r).",
    input_schema={
        "type": "object",
        "properties": {"n": {"type": "integer"}, "r": {"type": "integer"}},
        "required": ["n", "r"],
    },
    handler=_combinations,
))
REGISTRY.register(Tool(
    name="matrix_2x2_invert",
    description="2x2 행렬 [[a,b],[c,d]] 역행렬.",
    input_schema={
        "type": "object",
        "properties": {
            "a": {"type": "number"}, "b": {"type": "number"},
            "c": {"type": "number"}, "d": {"type": "number"},
        },
        "required": ["a", "b", "c", "d"],
    },
    handler=_matrix_2x2_invert,
))
REGISTRY.register(Tool(
    name="factorial",
    description="n! (n ≤ 1000).",
    input_schema={"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]},
    handler=_factorial,
))
REGISTRY.register(Tool(
    name="fibonacci",
    description="F(n) + 수열 (n ≤ 100).",
    input_schema={"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]},
    handler=_fibonacci,
))
REGISTRY.register(Tool(
    name="percentile",
    description="값의 p-percentile (선형 보간).",
    input_schema={
        "type": "object",
        "properties": {"values_csv": {"type": "string"}, "p": {"type": "number"}},
        "required": ["values_csv", "p"],
    },
    handler=_percentile,
))
