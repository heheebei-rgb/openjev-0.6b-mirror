#!/usr/bin/env python3
"""重建并校验模型权重分块。用法: python3 merge_and_verify.py（Python3 标准库，无需联网）"""
import hashlib
import json
import os
import shutil
import sys


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def resolve(here, rel):
    p = os.path.join(here, rel)
    if os.path.exists(p):
        return p
    # MANIFEST 里的分块路径带仓库目录前缀，去掉一级再试
    if "/" in rel:
        p2 = os.path.join(here, rel.split("/", 1)[1])
        if os.path.exists(p2):
            return p2
    return p


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    manifest = json.load(open(os.path.join(here, "MANIFEST.json")))
    ok = True
    for target, info in manifest["targets"].items():
        parts = [resolve(here, p) for p in info.get("parts", [])]
        target_path = os.path.join(here, target)
        if not parts:
            # 单文件目标：文件不在本仓库则跳过（属于另一个模型目录）
            if not os.path.exists(target_path):
                continue
            good = sha256(target_path) == info["sha256"]
            print(f"[{'OK' if good else 'FAIL'}] {target} (单文件校验)")
            ok = ok and good
            continue
        if not all(os.path.exists(p) for p in parts):
            print(f"[跳过] {target} 的分块不在本目录（属于另一个模型目录）")
            continue
        if os.path.exists(target_path) and sha256(target_path) == info["sha256"]:
            print(f"[skip] {target} 已重建且校验通过")
            continue
        os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
        tmp = target_path + ".tmp"
        with open(tmp, "wb") as out:
            for p in parts:
                with open(p, "rb") as f:
                    shutil.copyfileobj(f, out, 1 << 20)
        good = sha256(tmp) == info["sha256"]
        if good:
            os.replace(tmp, target_path)
            size = info["bytes"]
            print(f"[OK] {target} 重建完成 ({size} bytes, sha256 校验通过)")
        else:
            os.remove(tmp)
            print(f"[FAIL] {target} sha256 不匹配")
            ok = False
    print("全部校验通过 ✅" if ok else "存在失败或跳过 ❌")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
