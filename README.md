# Kuma

AI agent recommending answers to messages depending on the conversation history,
the person and the mood the user chooses.

## Getting Started

1. Install **UV** by following the instructions [here](https://docs.astral.sh/uv/getting-started/installation/#installing-uv).
2. Clone this repository:

   ```bash
   git clone git@github.com:the3neurons/kuma.git
   ```
   
3. Install dependencies:

   ```bash
   uv sync
   ```

4. Install the pre-commit hook:

   ```bash
   uv run pre-commit install --hook-type commit-msg
   ```

You're good to go!

## Contributing

- Never create your branches from the main branch, but rather from the develop
  branch.
- Create your branches on GitHub, they will already be named correctly (it 
  should have the number and the name of the issue it's linked).
- Format your files before commiting.
  The pre-commit hook should handle this automatically.
- Issues names must follow the same naming convention than the commits (see next
  bullet point).
- Name your commits by specifying the type of it and the file/feature edited.
  The pre-commit hook should also handle this be blocking commits that are not
  named correctly:

  - `fix`: A bug fix. Correlates with PATCH in SemVer
  - `feat`: A new feature. Correlates with MINOR in SemVer
  - `docs`: Documentation only changes
  - `style`: Changes that do not affect the meaning of the code (white-space,
    formatting, missing semicolons, ...)
  - `refactor`: A code change that neither fixes a bug nor adds a feature
  - `perf`: A code change that improves performance
  - `test`: Adding missing or correcting existing tests
  - `build`: Changes that affect the build system or external dependencies 
    (example scopes: pip, docker, npm)
  - `ci`: Changes to CI configuration files and scripts (example scopes: 
    GitLabCI)
  
  E.g.: `feat(main.py): add sign up button`
