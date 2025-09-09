#!/usr/bin/env python3
"""
Standalone NetCDF extractor.

Reads a NetCDF file, separates metadata (global attrs + variable attrs/dims)
from measurement arrays, cleans fill values, and prints summaries and details
to the console.

Usage (PowerShell):
  python netcdf_extractor.py "C:\\Users\\surya\\Downloads\\nodc_1900121_prof.nc"

This script is self-contained and does not modify existing project files.
"""

from __future__ import annotations

import sys
import os
import glob
import json
from typing import Any, Dict, Tuple

import numpy as np
from netCDF4 import Dataset


def open_netcdf(path: str) -> Dataset:
    return Dataset(path, mode="r")


def collect_global_metadata(ds: Dataset) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    for attr in ds.ncattrs():
        value = getattr(ds, attr)
        # Ensure JSON serializable
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="ignore")
        meta[attr] = value
    return meta


def collect_dimensions(ds: Dataset) -> Dict[str, Any]:
    dims: Dict[str, Any] = {}
    for name, dim in ds.dimensions.items():
        dims[name] = {
            "size": (len(dim) if not dim.isunlimited() else "UNLIMITED"),
            "isunlimited": bool(dim.isunlimited()),
        }
    return dims


def decode_fill_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return value


def variable_summary(var) -> Dict[str, Any]:
    var_meta: Dict[str, Any] = {
        "dtype": str(var.dtype),
        "dimensions": list(var.dimensions),
        "shape": list(var.shape),
        "attributes": {},
    }
    for attr in var.ncattrs():
        var_meta["attributes"][attr] = decode_fill_value(getattr(var, attr))
    return var_meta


def separate_metadata_and_measurements(ds: Dataset) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    metadata: Dict[str, Any] = {
        "global_attributes": collect_global_metadata(ds),
        "dimensions": collect_dimensions(ds),
        "variables": {},
    }
    measurements: Dict[str, Any] = {}

    for name, var in ds.variables.items():
        metadata["variables"][name] = variable_summary(var)
        # Decide if variable is metadata-like (character arrays / scalars) or measurement-like (numeric arrays)
        is_char = np.issubdtype(var.dtype, np.character)
        is_scalar = var.ndim == 0
        is_likely_metadata = is_char or is_scalar

        # Extract the data array lazily
        try:
            data = var[:]
        except Exception as e:
            measurements[name] = {"error": f"Failed to read data: {e}"}
            continue

        # Clean fill values if present
        fill_value = getattr(var, "_FillValue", None)
        if fill_value is not None:
            fill_value = decode_fill_value(fill_value)
            try:
                data = np.array(data)
                # For numeric arrays, replace fill with np.nan
                if np.issubdtype(data.dtype, np.number):
                    with np.errstate(invalid="ignore"):
                        data = np.where(data == fill_value, np.nan, data)
                else:
                    # For non-numeric (e.g., char), replace with empty string
                    data = np.where(data == fill_value, "", data)
            except Exception:
                # If comparison fails, keep original
                pass

        # Store data depending on type
        if is_likely_metadata:
            # Convert small arrays to lists for JSON
            try:
                metadata["variables"][name]["data_preview"] = _preview_array(data)
            except Exception:
                metadata["variables"][name]["data_preview"] = "<unavailable>"
        else:
            measurements[name] = _summarize_data_array(name, data)

    return metadata, measurements


def _preview_array(arr: Any, max_items: int = 50) -> Any:
    try:
        a = np.array(arr)
        if a.size <= max_items:
            return a.tolist()
        # For larger arrays, provide shape and head
        flat = a.ravel()
        head = flat[:max_items].tolist()
        return {"shape": list(a.shape), "head": head}
    except Exception:
        # If conversion fails, fall back to str
        return str(arr)


def _summarize_data_array(name: str, arr: Any) -> Dict[str, Any]:
    a = np.array(arr)
    summary: Dict[str, Any] = {
        "shape": list(a.shape),
        "dtype": str(a.dtype),
    }
    try:
        if np.issubdtype(a.dtype, np.number):
            valid = a[~np.isnan(a)] if a.size and np.issubdtype(a.dtype, np.floating) else a
            # Use nan-aware summaries for float
            summary.update({
                "min": float(np.nanmin(a)) if a.size else None,
                "max": float(np.nanmax(a)) if a.size else None,
                "mean": float(np.nanmean(a)) if a.size else None,
                "sample": _preview_array(a, 20),
            })
        else:
            summary.update({
                "sample": _preview_array(a, 50)
            })
    except Exception:
        summary["sample"] = _preview_array(a, 20)
    return summary


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        # Auto-detect .nc in current directory
        candidates = sorted(glob.glob("*.nc"))
        if len(candidates) == 1:
            path = candidates[0]
            print(f"No path provided. Auto-detected NetCDF file: {path}")
        elif len(candidates) > 1:
            print("Multiple .nc files found. Please specify one of:")
            for p in candidates:
                print(f"  - {p}")
            print("\nUsage: python netcdf_extractor.py <path_to_nc_file>")
            sys.exit(1)
        else:
            print("No .nc file found in current directory.")
            print("Usage: python netcdf_extractor.py <path_to_nc_file>")
            sys.exit(1)
    else:
        path = argv[1]

    if not os.path.exists(path):
        print(f"File not found: {path}")
        sys.exit(1)
    ds = open_netcdf(path)
    try:
        metadata, measurements = separate_metadata_and_measurements(ds)

        # Show only global attributes
        print("\n=== Global Attributes ===")
        print(json.dumps(metadata.get("global_attributes", {}), indent=2, default=str))

        # print("\n=== Dimensions ===")
        # print(json.dumps(metadata.get("dimensions", {}), indent=2, default=str))

        # print("\n=== Measurement Arrays (summary) ===")
        # print(json.dumps(measurements, indent=2, default=str))

    finally:
        ds.close()


if __name__ == "__main__":
    main(sys.argv)


