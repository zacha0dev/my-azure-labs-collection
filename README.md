
# My Azure Labs Collection 
This is a collection of **hands-on Azure engineering labs** built to explore cloud concepts through **real Bicep deployments**, **PowerShell automation**, and **custom service integrations**. Each lab is lightweight, modular, and safe to test in your own sandbox environment.

> 💡 **Tip:** These labs are best used in a *sandbox or trial subscription*. Always run the cleanup script when done to avoid unwanted costs.

### How to Use These Labs
Each folder represents a focused lab area that you can run and explore independently.  

| Section | Description |
|----------|--------------|
| [**Bicep**](./docs/bicep.md) | Learn modern IaC (Infrastructure as Code) using Bicep. Includes deploy, what-if, and cleanup scripts. |
| [**Custom Services**](./custom-services/.custom-services.md) | Small, self-contained labs that focus on Azure services like Storage, Networking, and Monitoring. |

### Cleanup
Each lab includes its own cleanup.ps1 script to safely delete all lab-created resources.

> Reference the `./scripts/cleanup.ps1` for each deployment.

You can delete:
- A single resource group
- Or all groups matching a specific tag (like DeploymentType=Lab)
```
# Example bulk delete of all Lab RGs
./cleanup.ps1 -Force -NoWait
```

</br>

---

### Contributions
Contributions are welcome! If you’d like to improve a lab, fix a script, or add new examples:

1. Fork this repo
2. Create a branch `(feature/new-lab)`
3. Submit a pull request

> Direct pushes to `main` are restricted.

### Connect With Me 
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue "LinkedIn")](https://www.linkedin.com/in/zacharythomasallen/) - [![GitHub](https://img.shields.io/badge/GitHub-Profile-black "GitHub")](https://github.com/zacha0dev)

_Last updated: October 2025_  </br>
_Version: 1.0 (Initial Release)_
