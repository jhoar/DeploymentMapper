package com.esa.deploymentmapper.util;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class NormalizationUtilTest {

    @Test
    void normalize_trims_lowers_and_replaces_spaces() {
        assertThat(NormalizationUtil.normalize("  Prod Env  ")).isEqualTo("prod_env");
    }

    @Test
    void normalize_handles_null() {
        assertThat(NormalizationUtil.normalize(null)).isEqualTo("");
    }
}
