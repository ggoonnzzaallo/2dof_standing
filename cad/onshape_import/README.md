# Final Onshape CAD import

The Onshape model supplied by the user is the final design source. The earlier generated CAD is provisional and must not determine the new training model.

Nine separately exported STEP components were inspected on 31 October 2026. Cleaned-up product names are present. Both servo files are named LOWER SERVO internally; the filename suffix is not an upper/lower assignment. Geometry import places both servo copies at identical local coordinates, so these files do not establish their distinct assembly poses. Hardware placements cannot safely be inferred from those exports.

A whole-assembly STEP export is needed before making a reliable colored assembly/joint review. Export the assembly tab in its upright pose, keeping component solids separate within one STEP file rather than exporting unique parts individually. Upper/lower aliases will be assigned from assembly instance placements and checked with the user. No joint axes, component placements or simulated mass properties have been finalized.

See inspection.json for source filenames, product names and checksums. Original Downloads files are unmodified.
