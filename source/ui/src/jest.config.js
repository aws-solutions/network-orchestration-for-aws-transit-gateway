module.exports = {
    roots: ["<rootDir>"],
    testMatch: ["**/*.test.ts"],
    transform: {
        "^.+\\.tsx?$": "ts-jest",
    },
    coverageReporters: ["text", ["lcov", { projectRoot: "../../" }]],
    setupFiles: ["./setJestEnvironmentVariables.ts"],
    moduleFileExtensions: ["ts", "tsx", "js", "jsx", "json", "node"],
};
