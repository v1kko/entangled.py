{
  description = "Python portt of Entangled";

  inputs.pyproject-nix.url = "github:pyproject-nix/pyproject.nix";
  inputs.pyproject-nix.inputs.nixpkgs.follows = "nixpkgs";
  inputs.flake-utils.url = "github:numtide/flake-utils";

  inputs.brei_flake.url = "github:entangled/brei";
  inputs.repl-session_flake.url = "github:entangled/repl-session";

  outputs = { nixpkgs, pyproject-nix, flake-utils, brei_flake, repl-session_flake, ... }: flake-utils.lib.eachDefaultSystem (system:
  let

    project = pyproject-nix.lib.project.loadPyproject {
      projectRoot = ./.;
    };

    pythonAttr = "python3";
    overlay = final: prev: {
      pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
        (python-final: python-prev: { 
          brei = brei_flake.packages.${system}.default; 
          repl-session = repl-session_flake.packages.${system}.default; 
          argh = python-prev.argh.overridePythonAttrs(old: rec {
            version = "0.30.5";
            src = python-final.fetchPypi {
              pname = "argh";
              inherit version;
              sha256 = "sha256-s339YXoJ0ZpKe8rtDgYLKIvHrI39wPrPiGpJol/zNyg=";
            };
            doCheck = false;
          });
          rich = python-prev.rich.overridePythonAttrs(old: rec {
            version = "13.8.1";
            src = final.fetchFromGitHub {
              owner = "Textualize";
              repo = "rich";
              rev = "refs/tags/v${version}";
              sha256 = "sha256-k+a64GDGzRDprvJz7s9Sm4z8jDV5TZ+CZLMgXKXXonM=";
            };
            doCheck = false;
          });
          rich-click = python-prev.rich-click.overridePythonAttrs(old: rec {
            version = "1.9.4";
            src = final.fetchFromGitHub {
              owner = "ewels";
              repo = "rich-click";
              tag = "v${version}";
              sha256 = "sha256-L39MlMMRh39ksTYi32ivYJqMMJ7lQsSQH6PhZQeSqpg=";
            };
            doCheck = false;
          });
          tomlkit = python-prev.tomlkit.overridePythonAttrs(old: rec {
            version = "0.12.5";
            pname = "tomlkit";
            src = final.fetchPypi {
              inherit pname version;
              hash = "sha256-7vNPujmDTU1rc8m6fz5NHEF6Tlb4mn6W4JDdDSS4+zw=";
            };
            doCheck = false;
          });
          msgspec = python-prev.msgspec.overridePythonAttrs(old: rec {
            version = "0.20.0";
            src = final.fetchFromGitHub {
              owner = "jcrist";
              repo = "msgspec";
              tag = "${version}";
              sha256 = "sha256-DWDmnSuo12oXl9NVfNhIOtWrQeJ9DMmHxOyHY33Datk=";
            };
            build-system = [ python-final.setuptools-scm ];
          });
        })
      ];
    };
  in
  let
    pkgs = import nixpkgs { inherit system; overlays = [ overlay ]; };
    python = pkgs.${pythonAttr};
    pythonEnv = python.withPackages (project.renderers.withPackages { inherit python; });
  in
  {
    devShells.default = pkgs.mkShell { packages = [ pythonEnv ]; };
    packages.default = python.pkgs.buildPythonPackage (project.renderers.buildPythonPackage { inherit python; });
  });
}
