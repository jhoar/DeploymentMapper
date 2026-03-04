package com.esa.deploymentmapper.util;

import java.util.Locale;

public final class NormalizationUtil {
    private NormalizationUtil() {
    }

    public static String normalize(String input) {
        if (input == null) {
            return "";
        }
        return input.trim().toLowerCase(Locale.ROOT).replace(" ", "_");
    }

    public static String clean(String input) {
        if (input == null) {
            return "";
        }
        return input.trim();
    }
}
