{
  description = "JPAMB: Java Program Analysis Micro Benchmarks";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/ca77296380960cd497a765102eeb1356eb80fed0";
    flake-utils.url = "github:numtide/flake-utils";
    jvm2json.url = "github:kalhauge/jvm2json";
    jvm2json.inputs.nixpkgs.follows = "nixpkgs";
  };
  outputs =
    {
      nixpkgs,
      flake-utils,
      jvm2json,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells = {
          default = pkgs.mkShell {
            name = "jpamb";
            packages = with pkgs; [
              jdt-language-server
              jdk
              maven
              jvm2json.packages.${system}.default
              uv
            ];
          };
        };

        packages = {
          docker = pkgs.dockerTools.buildImage {
            name = "jpamb";
            tag = "latest";

            copyToRoot = pkgs.buildEnv {
              name = "jpamb-env";
              paths = with pkgs; [
                jdk
                maven
                jvm2json.packages.${system}.default
                uv
                python3
                bash
                coreutils
              ];
            };

            config = {
              Cmd = [ "${pkgs.bash}/bin/bash" ];
              WorkingDir = "/workspace";
              Env = [
                "PATH=${pkgs.jdk}/bin:${pkgs.maven}/bin:${jvm2json.packages.${system}.default}/bin:${pkgs.uv}/bin:${pkgs.python3}/bin:${pkgs.bash}/bin:${pkgs.coreutils}/bin"
                "JAVA_HOME=${pkgs.jdk}"
              ];
            };
          };

          default = pkgs.dockerTools.buildImage {
            name = "jpamb";
            tag = "latest";

            copyToRoot = pkgs.buildEnv {
              name = "jpamb-env";
              paths = with pkgs; [
                jdk
                maven
                jvm2json.packages.${system}.default
                uv
                python3
                bash
                coreutils
              ];
            };

            config = {
              Cmd = [ "${pkgs.bash}/bin/bash" ];
              WorkingDir = "/workspace";
              Env = [
                "PATH=${pkgs.jdk}/bin:${pkgs.maven}/bin:${jvm2json.packages.${system}.default}/bin:${pkgs.uv}/bin:${pkgs.python3}/bin:${pkgs.bash}/bin:${pkgs.coreutils}/bin"
                "JAVA_HOME=${pkgs.jdk}"
              ];
            };
          };
        };
      }
    );
}
