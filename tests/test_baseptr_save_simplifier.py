
import os.path

import nose.tools

import angr
import ailment
from angr.analyses.decompiler.optimization_passes.base_ptr_save_simplifier import BasePointerSaveSimplifier

test_location = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'binaries', 'tests')


def _get_block(clinic, addr):

    for (block_addr, _), block in clinic._blocks.items():
        if block_addr == addr:
            return block
    return None


def test_baseptr_save_simplifier_amd64():

    # decompile all:main and make sure the first and the last blocks do not save or restore to rbp
    bin_path = os.path.join(test_location, "x86_64", "all")
    proj = angr.Project(bin_path, auto_load_libs=False)

    cfg = proj.analyses.CFG(data_references=True)

    optimization_passes = [ BasePointerSaveSimplifier ]
    main_func = cfg.functions['main']
    dec = proj.analyses.Decompiler(main_func, cfg=cfg, optimization_passes=optimization_passes)

    entry_block = _get_block(dec.clinic, main_func.addr)
    endpoint_block = _get_block(dec.clinic, next(iter(main_func.endpoints)).addr)

    nose.tools.assert_is_not_none(entry_block)
    nose.tools.assert_is_not_none(endpoint_block)

    for stmt in entry_block.statements:
        if isinstance(stmt, ailment.Stmt.Store) \
                and isinstance(stmt.data, ailment.Expr.StackBaseOffset):
            assert False, "Found a base-pointer saving statement in the first block."

    for stmt in endpoint_block.statements:
        if isinstance(stmt, ailment.Stmt.Assignment) \
                and isinstance(stmt.dst, ailment.Expr.Register) \
                and stmt.dst.reg_offset == proj.arch.bp_offset:
            assert False, "Found a base-pointer restoring statement in the last block."


def check_bp_save_fauxware(arch):
    p = angr.Project(os.path.join(test_location, arch, 'fauxware'), auto_load_libs=False)
    cfg = p.analyses.CFGFast()
    main = p.kb.functions['main']
    optimization_passes = [ BasePointerSaveSimplifier ]
    dra = p.analyses.Decompiler(main, cfg=cfg, optimization_passes=optimization_passes)
    first_block_stmts = dra.codegen._sequence.nodes[0].nodes[0].statements
    for stmt in first_block_stmts:
        if isinstance(stmt, ailment.Stmt.Store):
            nose.tools.assert_false(
                (isinstance(stmt.data, ailment.Expr.Register)
                 and stmt.data.reg_offset == p.arch.bp_offset)
                or (isinstance(stmt.data, ailment.Expr.StackBaseOffset)
                    and stmt.data.offset == 0))


def test_bp_save_amd64_fauxware():
    check_bp_save_fauxware('x86_64')


def test_bp_save_armel_fauxware():
    check_bp_save_fauxware('armel')


if __name__ == "__main__":
    test_baseptr_save_simplifier_amd64()
    test_bp_save_amd64_fauxware()
    test_bp_save_armel_fauxware()
