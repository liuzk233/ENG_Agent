"""
BGE-M3 本地模型测试脚本

验证 GPU 环境和模型加载是否正常。
"""

import sys


def test_cuda():
    """测试 CUDA 是否可用"""
    print("=" * 50)
    print("1. 测试 CUDA 环境")
    print("=" * 50)

    try:
        import torch
        print(f"   PyTorch 版本: {torch.__version__}")
        print(f"   CUDA 可用: {torch.cuda.is_available()}")

        if torch.cuda.is_available():
            print(f"   CUDA 版本: {torch.version.cuda}")
            print(f"   GPU 数量: {torch.cuda.device_count()}")
            print(f"   GPU 名称: {torch.cuda.get_device_name(0)}")
            print(f"   显存总量: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
            return True
        else:
            print("   ⚠️ CUDA 不可用，将使用 CPU（速度较慢）")
            return False
    except ImportError:
        print("   ❌ PyTorch 未安装，请运行: pip install torch")
        return False


def test_bge_m3():
    """测试 BGE-M3 模型加载和推理"""
    print("\n" + "=" * 50)
    print("2. 测试 BGE-M3 模型")
    print("=" * 50)

    try:
        from FlagEmbedding import BGEM3FlagModel
        print("   ✅ FlagEmbedding 已安装")
    except ImportError:
        print("   ❌ FlagEmbedding 未安装")
        print("   请运行: pip install FlagEmbedding")
        return False

    print("\n   正在加载模型（首次运行需下载约 2.5GB）...")

    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"

        model = BGEM3FlagModel(
            "BAAI/bge-m3",
            use_fp16=True,  # FP16 节省显存
            device=device,
        )
        print(f"   ✅ 模型加载成功 (设备: {device})")

        # 测试推理
        print("\n   测试向量化...")
        test_texts = [
            "This is a test sentence.",
            "这是中文测试句子。",
            "Machine learning is transforming the world.",
        ]

        output = model.encode(
            test_texts,
            batch_size=3,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )

        embeddings = output['dense_vecs']
        print(f"   ✅ 向量化成功！")
        print(f"   向量维度: {embeddings.shape[1]}")
        print(f"   向量数量: {embeddings.shape[0]}")

        # 显示显存使用
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**3
            reserved = torch.cuda.memory_reserved() / 1024**3
            print(f"   显存已分配: {allocated:.2f} GB")
            print(f"   显存已保留: {reserved:.2f} GB")

        return True

    except Exception as e:
        print(f"   ❌ 模型加载失败: {e}")
        return False


def test_embedder_module():
    """测试项目 embedder 模块"""
    print("\n" + "=" * 50)
    print("3. 测试项目 embedder 模块")
    print("=" * 50)

    try:
        import os
        os.environ["EMBEDDING_BACKEND"] = "bge-m3"

        from src.rag.embedder import get_embedder, BGEM3Embedding

        embedder = get_embedder()
        print(f"   ✅ get_embedder() 返回类型: {type(embedder).__name__}")

        # 测试向量化
        texts = ["Hello world", "你好世界"]
        embeddings = embedder.embed(texts)

        print(f"   ✅ 向量化成功，维度: {len(embeddings[0])}")
        return True

    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n🚀 BGE-M3 环境检测与测试\n")

    results = []
    results.append(("CUDA 环境", test_cuda()))
    results.append(("BGE-M3 模型", test_bge_m3()))
    results.append(("项目模块集成", test_embedder_module()))

    print("\n" + "=" * 50)
    print("📋 测试结果汇总")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有测试通过！可以开始使用 BGE-M3 本地模型。")
        print("\n使用方法：")
        print("  在 .env 文件中设置: EMBEDDING_BACKEND=bge-m3")
        print("  然后运行: python src/rag/builder.py -i data/processed/markdown -s <大纲路径>")
    else:
        print("⚠️ 部分测试未通过，请检查上述错误信息。")
    print("=" * 50 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
