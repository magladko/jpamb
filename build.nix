{
  lib,
  python3Packages,
  self,

  jdk,
  maven,
  jvm2json,
}:
let
  pyproject = lib.importTOML ./pyproject.toml;
in
python3Packages.buildPythonApplication {
  pname = pyproject.project.name;
  version = pyproject.project.version;
  pyproject = true;
  src = self;

  build-system = with python3Packages; [ setuptools ];

  dontCheckRuntimeDeps = true;

  dependencies = [
    maven
    jvm2json
    jdk
  ]
  ++ (with python3Packages; [
    pyyaml
    click
    hypothesis
    loguru
    matplotlib
    # plotly
    tree-sitter-grammars.tree-sitter-java
    tree-sitter
    python3Packages.z3-solver
    python3Packages.z3
  ]);

  makeWrapperArgs = [
    "--set"
    "JAVA_HOME"
    jdk
  ];
  # meta = {
  #   # ...
  # };
}
