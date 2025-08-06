try:
    import hll_auto_join
    print("Import worked!")
except Exception as e:
    print("Import failed:", e)
    import traceback
    traceback.print_exc()