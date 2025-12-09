import { useState, useEffect, useMemo, useCallback } from "react"
import {
  type ColumnDef,
  type ColumnFiltersState,
  type SortingState,
  type VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"
import { ArrowUpDown, Plus, Download, Trash2, Search, Play, Loader2, Edit, MoreHorizontal, ChevronDown } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuCheckboxItem,
} from "@/components/ui/dropdown-menu"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"

import {
  type Agency,
  type List,
  type BatchScrapeResult,
  type County,
  getAgencies,
  getAgencyStats,
  getLists,
  createList,
  deleteList,
  addAgencyToList,
  downloadListCSV,
  downloadListJSON,
  startBatchScrape,
  getCounties,
  addCounty,
  updateCounty,
  deleteCounty,
  updateAgency,
  deleteAgency,
} from "@/lib/api"

function App() {
  const [agencies, setAgencies] = useState<Agency[]>([])
  const [lists, setLists] = useState<List[]>([])
  const [stats, setStats] = useState<{ total_agencies: number; by_state: Record<string, number> } | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [addingToList, setAddingToList] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  const [currentOffset, setCurrentOffset] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [batchScraping, setBatchScraping] = useState(false)
  const [batchResults, setBatchResults] = useState<BatchScrapeResult[] | null>(null)
  const [saveToDb, setSaveToDb] = useState(true)

  // Counties management
  const [counties, setCounties] = useState<County[]>([])
  const [countyDialogOpen, setCountyDialogOpen] = useState(false)
  const [editingCounty, setEditingCounty] = useState<County | null>(null)
  const [newCountyState, setNewCountyState] = useState("")
  const [newCountyLocation, setNewCountyLocation] = useState("")
  const [editingCountyId, setEditingCountyId] = useState<number | null>(null)
  const [editingCountyState, setEditingCountyState] = useState("")
  const [editingCountyLocation, setEditingCountyLocation] = useState("")

  // Filters
  const [stateFilter, setStateFilter] = useState("")
  const [locationFilter, setLocationFilter] = useState("")
  const [npiFilter, setNpiFilter] = useState("")

  // Dialog states
  const [createListOpen, setCreateListOpen] = useState(false)
  const [selectedListId, setSelectedListId] = useState<string>("")
  const [newListName, setNewListName] = useState("")
  const [newListDescription, setNewListDescription] = useState("")

  // Agency editing state
  const [editingAgencyId, setEditingAgencyId] = useState<string | null>(null)
  const [editingAgencyData, setEditingAgencyData] = useState<Partial<Agency>>({})

  // Table state
  const [sorting, setSorting] = useState<SortingState>([])
  const [countySorting, setCountySorting] = useState<SortingState>([])
  const [batchResultsSorting, setBatchResultsSorting] = useState<SortingState>([])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})
  const [rowSelection, setRowSelection] = useState({})

  // Load initial data
  useEffect(() => {
    loadAgencies()
    loadLists()
    loadCounties()
  }, [])

  const loadCounties = async () => {
    try {
      const data = await getCounties()
      setCounties(data.counties)
    } catch (err) {
      console.error("Failed to load counties:", err)
    }
  }

  const handleAddCounty = async () => {
    if (!newCountyState.trim() || !newCountyLocation.trim()) {
      setError("State and location are required")
      return
    }

    try {
      await addCounty(newCountyState, newCountyLocation)
      setNewCountyState("")
      setNewCountyLocation("")
      setCountyDialogOpen(false)
      await loadCounties()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add county")
    }
  }

  const handleUpdateCounty = async () => {
    if (!editingCounty || !newCountyState.trim() || !newCountyLocation.trim()) {
      setError("State and location are required")
      return
    }

    try {
      await updateCounty(editingCounty.id, newCountyState, newCountyLocation)
      setEditingCounty(null)
      setNewCountyState("")
      setNewCountyLocation("")
      setCountyDialogOpen(false)
      await loadCounties()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update county")
    }
  }

  const handleDeleteCounty = async (countyId: number) => {
    if (!confirm("Are you sure you want to delete this county?")) {
      return
    }

    try {
      await deleteCounty(countyId)
      await loadCounties()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete county")
    }
  }

  const startEditingCounty = (county: County) => {
    setEditingCountyId(county.id)
    setEditingCountyState(county.state)
    setEditingCountyLocation(county.location)
  }

  const cancelEditingCounty = () => {
    setEditingCountyId(null)
    setEditingCountyState("")
    setEditingCountyLocation("")
  }

  const saveEditingCounty = async (countyId: number) => {
    if (!editingCountyState.trim() || !editingCountyLocation.trim()) {
      setError("State and location are required")
      return
    }

    try {
      await updateCounty(countyId, editingCountyState, editingCountyLocation)
      setEditingCountyId(null)
      setEditingCountyState("")
      setEditingCountyLocation("")
      await loadCounties()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update county")
    }
  }

  const openAddDialog = () => {
    setEditingCounty(null)
    setNewCountyState("")
    setNewCountyLocation("")
    setCountyDialogOpen(true)
  }

  const loadAgencies = async (append: boolean = false) => {
    if (append) {
      setLoadingMore(true)
    } else {
      setLoading(true)
      setAgencies([])
      setCurrentOffset(0)
      setHasMore(true)
    }
    setError(null)
    
    try {
      const filters: any = {}
      if (stateFilter) filters.state = stateFilter.toUpperCase()
      if (locationFilter) filters.location = locationFilter
      if (npiFilter) filters.npi = npiFilter
      
      const batchSize = 100
      const offset = append ? currentOffset : 0
      const data = await getAgencies({ ...filters, limit: batchSize, offset })
      
      if (append) {
        setAgencies(prev => [...prev, ...data.agencies])
      } else {
        setAgencies(data.agencies)
      }
      
      setCurrentOffset(offset + data.agencies.length)
      setHasMore(data.agencies.length === batchSize)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load agencies")
    } finally {
      if (append) {
        setLoadingMore(false)
      } else {
        setLoading(false)
      }
    }
  }

  const handleLoadMore = async () => {
    await loadAgencies(true)
  }

  const handleSelectAll = useCallback(() => {
    const allRowIds = agencies.reduce((acc, agency) => {
      acc[agency.id] = true
      return acc
    }, {} as Record<string, boolean>)
    setRowSelection(allRowIds)
  }, [agencies])

  const handleDeselectAll = useCallback(() => {
    setRowSelection({})
  }, [])

  const loadLists = async () => {
    try {
      const data = await getLists()
      setLists(data.lists)
    } catch (err) {
      console.error("Failed to load lists:", err)
    }
  }

  const loadStats = async () => {
    try {
      const data = await getAgencyStats()
      setStats(data)
    } catch (err) {
      console.error("Failed to load stats:", err)
    }
  }

  // Load stats on mount (stats is used in the UI)
  useEffect(() => {
    loadStats()
  }, [])

  const handleCreateList = async () => {
    if (!newListName.trim()) return
    try {
      const list = await createList(newListName, newListDescription)
      setLists([...lists, list])
      setNewListName("")
      setNewListDescription("")
      setCreateListOpen(false)
      setSelectedListId(list.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create list")
    }
  }

  const handleAddToList = async () => {
    if (!selectedListId) return
    
    const selectedRows = table.getFilteredSelectedRowModel().rows
    if (selectedRows.length === 0) {
      setError("Please select at least one agency")
      return
    }

    setError(null)
    setAddingToList(true)
    
    try {
      let successCount = 0
      let failCount = 0
      const errors: string[] = []

      // Process in batches to avoid overwhelming the server
      const batchSize = 10
      for (let i = 0; i < selectedRows.length; i += batchSize) {
        const batch = selectedRows.slice(i, i + batchSize)
        const batchPromises = batch.map(async (row) => {
          try {
            await addAgencyToList(selectedListId, row.original.id)
            successCount++
          } catch (err) {
            failCount++
            const agencyName = row.original.provider_name || row.original.agency_name || 'Unknown'
            errors.push(`${agencyName}: ${err instanceof Error ? err.message : 'Failed to add'}`)
          }
        })
        await Promise.all(batchPromises)
      }

      setRowSelection({})
      
      if (failCount > 0) {
        setError(`Added ${successCount} agencies. ${failCount} failed: ${errors.slice(0, 5).join('; ')}${errors.length > 5 ? '...' : ''}`)
      } else {
        alert(`Successfully added ${successCount} agencies to list`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add agencies to list")
    } finally {
      setAddingToList(false)
    }
  }

  const handleBulkDelete = async () => {
    const selectedRows = table.getFilteredSelectedRowModel().rows
    if (selectedRows.length === 0) {
      setError("Please select at least one agency to delete")
      return
    }

    const count = selectedRows.length
    if (!confirm(`Are you sure you want to delete ${count} agency/agencies? This action cannot be undone.`)) {
      return
    }

    setLoading(true)
    setError(null)

    try {
      let successCount = 0
      let failCount = 0
      const errors: string[] = []

      for (const row of selectedRows) {
        try {
          await deleteAgency(row.original.id)
          successCount++
        } catch (err) {
          failCount++
          const agencyName = row.original.provider_name || row.original.agency_name || 'Unknown'
          errors.push(`${agencyName}: ${err instanceof Error ? err.message : 'Failed to delete'}`)
        }
      }

      // Clear selection
      setRowSelection({})

      // Reload data
      await loadAgencies()

      // Show results
      if (failCount > 0) {
        setError(`Deleted ${successCount} agencies. ${failCount} failed: ${errors.join('; ')}`)
      } else {
        alert(`Successfully deleted ${successCount} agency/agencies`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bulk delete failed")
    } finally {
      setAddingToList(false)
    }
  }

  const handleDownload = (format: "csv" | "json") => {
    if (!selectedListId) return
    const list = lists.find((l) => l.id === selectedListId)
    if (!list) return

    if (format === "csv") {
      downloadListCSV(selectedListId, list.name)
    } else {
      downloadListJSON(selectedListId, list.name)
    }
  }

  const handleBatchScrape = async () => {
    if (!confirm(`This will scrape all state/county pairs from counties.csv. This may take a while. Continue?`)) {
      return
    }

    setBatchScraping(true)
    setBatchResults(null)
    setError(null)

    try {
      const results = await startBatchScrape(saveToDb)
      setBatchResults(results)
      
      // Reload agencies after batch scrape
      if (saveToDb) {
        await loadAgencies()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Batch scrape failed")
    } finally {
      setBatchScraping(false)
    }
  }

  const startEditingAgency = (agency: Agency) => {
    setEditingAgencyId(agency.id)
    setEditingAgencyData({
      provider_name: agency.provider_name || "",
      agency_name: agency.agency_name || "",
      phone: agency.phone || "",
      npi: agency.npi || "",
    })
  }

  const cancelEditingAgency = () => {
    setEditingAgencyId(null)
    setEditingAgencyData({})
  }

  const saveEditingAgency = async (agencyId: string) => {
    try {
      await updateAgency(agencyId, editingAgencyData)
      setEditingAgencyId(null)
      setEditingAgencyData({})
      await loadAgencies()
      await loadStats()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update agency")
    }
  }

  // Define columns
  const columns: ColumnDef<Agency>[] = useMemo(
    () => [
      {
        id: "select",
        header: () => {
          const allSelected = agencies.length > 0 && agencies.every(agency => (rowSelection as Record<string, boolean>)[agency.id])
          const someSelected = agencies.some(agency => (rowSelection as Record<string, boolean>)[agency.id])
          
          return (
            <Checkbox
              checked={allSelected || (someSelected && "indeterminate")}
              onCheckedChange={(value) => {
                if (value) {
                  handleSelectAll()
                } else {
                  handleDeselectAll()
                }
              }}
              aria-label="Select all"
            />
          )
        },
        cell: ({ row }) => (
          <Checkbox
            checked={row.getIsSelected()}
            onCheckedChange={(value) => row.toggleSelected(!!value)}
            aria-label="Select row"
          />
        ),
        enableSorting: false,
        enableHiding: false,
      },
      {
        accessorKey: "provider_name",
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            >
              Provider Name
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          )
        },
        cell: ({ row }) => {
          const agency = row.original
          const isEditing = editingAgencyId === agency.id

          if (isEditing) {
            return (
              <Input
                value={editingAgencyData.provider_name || ""}
                onChange={(e) => setEditingAgencyData({ ...editingAgencyData, provider_name: e.target.value })}
                className="h-8 w-full"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    saveEditingAgency(agency.id)
                  } else if (e.key === "Escape") {
                    cancelEditingAgency()
                  }
                }}
                autoFocus
              />
            )
          }

          return (
            <div
              className="font-medium cursor-pointer hover:bg-muted/50 px-2 py-1 rounded"
              onClick={() => startEditingAgency(agency)}
              title="Click to edit"
            >
              {agency.provider_name || agency.agency_name || "N/A"}
            </div>
          )
        },
      },
      {
        accessorKey: "npi",
        header: "NPI",
        cell: ({ row }) => {
          const agency = row.original
          const isEditing = editingAgencyId === agency.id

          if (isEditing) {
            return (
              <Input
                value={editingAgencyData.npi || ""}
                onChange={(e) => setEditingAgencyData({ ...editingAgencyData, npi: e.target.value })}
                className="h-8 w-full"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    saveEditingAgency(agency.id)
                  } else if (e.key === "Escape") {
                    cancelEditingAgency()
                  }
                }}
              />
            )
          }

          return (
            <div
              className="cursor-pointer hover:bg-muted/50 px-2 py-1 rounded"
              onClick={() => startEditingAgency(agency)}
              title="Click to edit"
            >
              {agency.npi || "N/A"}
            </div>
          )
        },
      },
      {
        id: "address",
        header: "Address",
        cell: ({ row }) => {
          const address = row.original.agency_addresses?.[0]
          if (!address) return "N/A"
          const parts = [address.street, address.city, address.state, address.zip].filter(Boolean)
          return <div>{parts.join(", ") || "N/A"}</div>
        },
      },
      {
        accessorKey: "phone",
        header: "Phone",
        cell: ({ row }) => {
          const agency = row.original
          const isEditing = editingAgencyId === agency.id

          if (isEditing) {
            return (
              <Input
                value={editingAgencyData.phone || ""}
                onChange={(e) => setEditingAgencyData({ ...editingAgencyData, phone: e.target.value })}
                className="h-8 w-full"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    saveEditingAgency(agency.id)
                  } else if (e.key === "Escape") {
                    cancelEditingAgency()
                  }
                }}
              />
            )
          }

          return (
            <div
              className="cursor-pointer hover:bg-muted/50 px-2 py-1 rounded"
              onClick={() => startEditingAgency(agency)}
              title="Click to edit"
            >
              {agency.phone || "N/A"}
            </div>
          )
        },
      },
      {
        accessorKey: "source_state",
        header: "State",
        cell: ({ row }) => <div>{row.getValue("source_state")}</div>,
      },
      {
        accessorKey: "source_location",
        header: "Location",
        cell: ({ row }) => <div>{row.getValue("source_location")}</div>,
      },
      {
        id: "actions",
        enableHiding: false,
        cell: ({ row }) => {
          const agency = row.original
          const isEditing = editingAgencyId === agency.id

          if (isEditing) {
            return (
              <div className="flex justify-end gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => saveEditingAgency(agency.id)}
                >
                  Save
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={cancelEditingAgency}
                >
                  Cancel
                </Button>
              </div>
            )
          }

          return (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="h-8 w-8 p-0">
                  <span className="sr-only">Open menu</span>
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Actions</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => startEditingAgency(agency)}
                >
                  <Edit className="mr-2 h-4 w-4" />
                  Edit
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => {
                    // Copy NPI to clipboard
                    if (agency.npi) {
                      navigator.clipboard.writeText(agency.npi)
                    }
                  }}
                >
                  Copy NPI
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => {
                    // Open detail URL in new tab
                    if (agency.detail_url) {
                      window.open(agency.detail_url, '_blank')
                    }
                  }}
                >
                  View Details
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={async () => {
                    if (confirm(`Delete agency "${agency.provider_name || agency.agency_name || 'Unknown'}"?`)) {
                      try {
                        await deleteAgency(agency.id)
                        await loadAgencies()
                      } catch (err) {
                        setError(err instanceof Error ? err.message : "Failed to delete agency")
                      }
                    }
                  }}
                  className="text-destructive"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )
        },
      },
    ],
    [editingAgencyId, editingAgencyData, rowSelection, agencies, handleSelectAll, handleDeselectAll]
  )

  const table = useReactTable({
    data: agencies,
    columns,
    enableRowSelection: true,
    getRowId: (row) => row.id,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    manualPagination: false,
    initialState: {
      pagination: {
        pageSize: 10000, // Show all rows, no pagination
      },
    },
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
    },
  })

  const selectedCount = Object.keys(rowSelection).length

  // Counties table columns with inline editing
  const countyColumns: ColumnDef<County>[] = useMemo(
    () => [
      {
        accessorKey: "state",
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            >
              State
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          )
        },
        cell: ({ row }) => {
          const county = row.original
          const isEditing = editingCountyId === county.id

          if (isEditing) {
            return (
              <Input
                value={editingCountyState}
                onChange={(e) => setEditingCountyState(e.target.value.toUpperCase())}
                className="h-8 w-20"
                maxLength={2}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    saveEditingCounty(county.id)
                  } else if (e.key === "Escape") {
                    cancelEditingCounty()
                  }
                }}
                autoFocus
              />
            )
          }

          return (
            <div
              className="font-medium cursor-pointer hover:bg-muted/50 px-2 py-1 rounded"
              onClick={() => startEditingCounty(county)}
              title="Click to edit"
            >
              {county.state}
            </div>
          )
        },
      },
      {
        accessorKey: "location",
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            >
              Location
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          )
        },
        cell: ({ row }) => {
          const county = row.original
          const isEditing = editingCountyId === county.id

          if (isEditing) {
            return (
              <Input
                value={editingCountyLocation}
                onChange={(e) => setEditingCountyLocation(e.target.value)}
                className="h-8 w-full"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    saveEditingCounty(county.id)
                  } else if (e.key === "Escape") {
                    cancelEditingCounty()
                  }
                }}
              />
            )
          }

          return (
            <div
              className="cursor-pointer hover:bg-muted/50 px-2 py-1 rounded"
              onClick={() => startEditingCounty(county)}
              title="Click to edit"
            >
              {county.location}
            </div>
          )
        },
      },
      {
        id: "actions",
        header: "Actions",
        enableHiding: false,
        cell: ({ row }) => {
          const county = row.original
          const isEditing = editingCountyId === county.id

          if (isEditing) {
            return (
              <div className="flex justify-end gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => saveEditingCounty(county.id)}
                >
                  Save
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={cancelEditingCounty}
                >
                  Cancel
                </Button>
              </div>
            )
          }

          return (
            <div className="flex justify-end gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => startEditingCounty(county)}
              >
                <Edit className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleDeleteCounty(county.id)}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </div>
          )
        },
      },
    ],
    [editingCountyId, editingCountyState, editingCountyLocation]
  )

  const [countyColumnFilters, setCountyColumnFilters] = useState<ColumnFiltersState>([])
  const [countySearchFilter, setCountySearchFilter] = useState("")

  // Filter counties based on search
  const filteredCounties = useMemo(() => {
    if (!countySearchFilter) return counties
    const searchLower = countySearchFilter.toLowerCase()
    return counties.filter(
      (county) =>
        county.state.toLowerCase().includes(searchLower) ||
        county.location.toLowerCase().includes(searchLower)
    )
  }, [counties, countySearchFilter])

  const countiesTable = useReactTable({
    data: filteredCounties,
    columns: countyColumns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    state: {
      sorting: countySorting,
      columnFilters: countyColumnFilters,
    },
    onSortingChange: setCountySorting,
    onColumnFiltersChange: setCountyColumnFilters,
  })

  // Batch scrape results table columns
  const batchResultsColumns: ColumnDef<BatchScrapeResult>[] = useMemo(
    () => [
      {
        accessorKey: "state",
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            >
              State
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          )
        },
        cell: ({ row }) => <div className="font-medium">{row.getValue("state")}</div>,
      },
      {
        accessorKey: "location",
        header: ({ column }) => {
          return (
            <Button
              variant="ghost"
              onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
            >
              Location
              <ArrowUpDown className="ml-2 h-4 w-4" />
            </Button>
          )
        },
        cell: ({ row }) => <div>{row.getValue("location")}</div>,
      },
      {
        id: "agencies_count",
        header: "Agencies Found",
        cell: ({ row }) => {
          const result = row.original
          return (
            <div className={result.error ? "text-destructive" : "text-green-600"}>
              {result.error ? "Error" : result.agencies.length}
            </div>
          )
        },
      },
      {
        id: "error",
        header: "Status",
        cell: ({ row }) => {
          const result = row.original
          return (
            <div className={result.error ? "text-destructive" : "text-green-600"}>
              {result.error ? `Error: ${result.error}` : "Success"}
            </div>
          )
        },
      },
    ],
    []
  )

  const batchResultsTable = useReactTable({
    data: batchResults || [],
    columns: batchResultsColumns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getRowId: (row, index) => `${row.state}-${row.location}-${index}`,
    state: {
      sorting: batchResultsSorting,
    },
    onSortingChange: setBatchResultsSorting,
  })

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8">
          <h1 className="text-4xl font-bold">🏥 NPIDB Agency Manager</h1>
          <p className="text-muted-foreground">Browse agencies, create lists, and download data</p>
        </div>

        {error && (
          <Card className="mb-6 border-destructive">
            <CardContent className="pt-6">
              <p className="text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        <Tabs defaultValue="agencies" className="w-full">
          <TabsList className="grid w-full max-w-md grid-cols-3">
            <TabsTrigger value="agencies">Agencies</TabsTrigger>
            <TabsTrigger value="batch-scraper">Batch Scraper</TabsTrigger>
            <TabsTrigger value="lists">Lists</TabsTrigger>
          </TabsList>

          <TabsContent value="agencies" className="mt-6">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Agencies</CardTitle>
                <CardDescription>
                  {agencies.length} agencies loaded
                  {stats && stats.total_agencies > agencies.length && (
                    <span className="text-muted-foreground">
                      {" "}({stats.total_agencies} total in database)
                    </span>
                  )}
                  {selectedCount > 0 && ` • ${selectedCount} selected`}
                </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    {selectedCount > 0 && (
                      <Button
                        variant="destructive"
                        onClick={handleBulkDelete}
                        disabled={loading}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete Selected ({selectedCount})
                      </Button>
                    )}
                    <Dialog open={createListOpen} onOpenChange={setCreateListOpen}>
                      <DialogTrigger asChild>
                        <Button variant="outline">
                          <Plus className="mr-2 h-4 w-4" />
                          New List
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Create New List</DialogTitle>
                          <DialogDescription>
                            Create a new list to save selected agencies
                          </DialogDescription>
                        </DialogHeader>
                        <div className="grid gap-4 py-4">
                          <div className="grid gap-2">
                            <Label htmlFor="list-name">List Name</Label>
                            <Input
                              id="list-name"
                              value={newListName}
                              onChange={(e) => setNewListName(e.target.value)}
                              placeholder="My Agency List"
                            />
                          </div>
                          <div className="grid gap-2">
                            <Label htmlFor="list-description">Description (optional)</Label>
                            <Input
                              id="list-description"
                              value={newListDescription}
                              onChange={(e) => setNewListDescription(e.target.value)}
                              placeholder="Description of this list"
                            />
                          </div>
                        </div>
                        <DialogFooter>
                          <Button onClick={handleCreateList}>Create List</Button>
                        </DialogFooter>
                      </DialogContent>
                    </Dialog>
                    
                    {selectedCount > 0 && (
                      <div className="flex gap-2">
                        <Select value={selectedListId} onValueChange={setSelectedListId}>
                          <SelectTrigger className="w-[200px]">
                            <SelectValue placeholder="Select a list" />
                          </SelectTrigger>
                          <SelectContent>
                            {lists.map((list) => (
                              <SelectItem key={list.id} value={list.id}>
                                {list.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <Button 
                          onClick={handleAddToList}
                          disabled={!selectedListId || addingToList}
                        >
                          {addingToList ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              Adding...
                            </>
                          ) : (
                            "Add to List"
                          )}
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="py-8 text-center text-muted-foreground">Loading agencies...</div>
                ) : addingToList ? (
                  <div className="py-8 text-center text-muted-foreground">
                    <Loader2 className="mr-2 h-4 w-4 animate-spin inline" />
                    Adding agencies to list...
                  </div>
                ) : (
                  <>
                    {/* Integrated Search/Filter Bar */}
                    <div className="flex items-center py-4 gap-4 flex-wrap">
                      <Input
                        placeholder="Filter agencies by name..."
                        value={(table.getColumn("provider_name")?.getFilterValue() as string) ?? ""}
                        onChange={(event) =>
                          table.getColumn("provider_name")?.setFilterValue(event.target.value)
                        }
                        className="max-w-sm"
                      />
                      <Input
                        placeholder="State (e.g., NC)"
                        value={stateFilter}
                        onChange={(e) => setStateFilter(e.target.value)}
                        maxLength={2}
                        className="max-w-[120px]"
                      />
                      <Input
                        placeholder="Location"
                        value={locationFilter}
                        onChange={(e) => setLocationFilter(e.target.value)}
                        className="max-w-[150px]"
                      />
                      <Input
                        placeholder="NPI"
                        value={npiFilter}
                        onChange={(e) => setNpiFilter(e.target.value)}
                        className="max-w-[150px]"
                      />
                      <Button onClick={() => loadAgencies(false)} variant="outline">
                        <Search className="mr-2 h-4 w-4" />
                        Apply Filters
                      </Button>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="outline" className="ml-auto">
                            Columns <ChevronDown className="ml-2 h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {table
                            .getAllColumns()
                            .filter(
                              (column) => typeof column.accessorFn !== "undefined" && column.getCanHide()
                            )
                            .map((column) => {
                              return (
                                <DropdownMenuCheckboxItem
                                  key={column.id}
                                  className="capitalize"
                                  checked={column.getIsVisible()}
                                  onCheckedChange={(value) =>
                                    column.toggleVisibility(!!value)
                                  }
                                >
                                  {column.id}
                                </DropdownMenuCheckboxItem>
                              )
                            })}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>

                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          {table.getHeaderGroups().map((headerGroup) => (
                            <TableRow key={headerGroup.id}>
                              {headerGroup.headers.map((header) => (
                                <TableHead key={header.id}>
                                  {header.isPlaceholder
                                    ? null
                                    : flexRender(
                                        header.column.columnDef.header,
                                        header.getContext()
                                      )}
                                </TableHead>
                              ))}
                            </TableRow>
                          ))}
                        </TableHeader>
                        <TableBody>
                          {table.getRowModel().rows?.length ? (
                            table.getRowModel().rows.map((row) => (
                              <TableRow
                                key={row.id}
                                data-state={row.getIsSelected() && "selected"}
                              >
                                {row.getVisibleCells().map((cell) => (
                                  <TableCell key={cell.id}>
                                    {flexRender(
                                      cell.column.columnDef.cell,
                                      cell.getContext()
                                    )}
                                  </TableCell>
                                ))}
                              </TableRow>
                            ))
                          ) : (
                            <TableRow>
                              <TableCell
                                colSpan={columns.length}
                                className="h-24 text-center"
                              >
                                No agencies found.
                              </TableCell>
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </div>
                    <div className="flex items-center justify-between space-x-2 py-4">
                      <div className="flex-1 text-sm text-muted-foreground">
                        {Object.keys(rowSelection).length} of{" "}
                        {agencies.length} row(s) selected
                        {stats && stats.total_agencies > agencies.length && (
                          <span className="text-muted-foreground">
                            {" "}({agencies.length} loaded of {stats.total_agencies} total)
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {hasMore && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handleLoadMore}
                            disabled={loadingMore}
                          >
                            {loadingMore ? (
                              <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Loading...
                              </>
                            ) : (
                              <>
                                Load More ({agencies.length} loaded)
                              </>
                            )}
                          </Button>
                        )}
                        {Object.keys(rowSelection).length > 0 && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handleDeselectAll}
                          >
                            Clear Selection
                          </Button>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="batch-scraper" className="mt-6">
            <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Batch Scraper</CardTitle>
                <CardDescription>
                  Scrape all state/county pairs from counties.csv ({counties.length} counties)
                </CardDescription>
              </div>
              <Button variant="outline" onClick={openAddDialog}>
                <Plus className="mr-2 h-4 w-4" />
                Add County
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4 mb-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={saveToDb}
                  onChange={(e) => setSaveToDb(e.target.checked)}
                  className="h-4 w-4"
                />
                <span className="text-sm">Save results to database</span>
              </label>
              <Button
                onClick={handleBatchScrape}
                disabled={batchScraping}
                variant="default"
              >
                {batchScraping ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Scraping...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Start Batch Scrape
                  </>
                )}
              </Button>
            </div>

            {/* Counties datatable */}
            <div className="space-y-4">
              <div className="flex items-center py-2">
                <Input
                  placeholder="Filter counties by state or location..."
                  value={countySearchFilter}
                  onChange={(event) => setCountySearchFilter(event.target.value)}
                  className="max-w-sm"
                />
              </div>
            <div className="border rounded-lg">
                <div className="max-h-96 overflow-y-auto">
                <Table>
                  <TableHeader>
                    {countiesTable.getHeaderGroups().map((headerGroup) => (
                      <TableRow key={headerGroup.id}>
                        {headerGroup.headers.map((header) => (
                          <TableHead key={header.id}>
                            {header.isPlaceholder
                              ? null
                              : flexRender(
                                  header.column.columnDef.header,
                                  header.getContext()
                                )}
                          </TableHead>
                        ))}
                    </TableRow>
                    ))}
                  </TableHeader>
                  <TableBody>
                    {countiesTable.getRowModel().rows?.length ? (
                      countiesTable.getRowModel().rows.map((row) => (
                        <TableRow
                          key={row.id}
                          data-state={row.getIsSelected() && "selected"}
                        >
                          {row.getVisibleCells().map((cell) => (
                            <TableCell key={cell.id}>
                              {flexRender(
                                cell.column.columnDef.cell,
                                cell.getContext()
                              )}
                        </TableCell>
                          ))}
                      </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell
                          colSpan={countyColumns.length}
                          className="h-24 text-center"
                        >
                          No counties added yet
                          </TableCell>
                        </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
              </div>
              {countySearchFilter && (
                <div className="text-sm text-muted-foreground">
                  Showing {countiesTable.getFilteredRowModel().rows.length} of {counties.length} counties
                </div>
              )}
            </div>
            
            {batchResults && batchResults.length > 0 && (
              <div className="mt-4 space-y-2">
                <h4 className="font-semibold">Batch Scrape Results:</h4>
                <div className="border rounded-lg">
                  <div className="max-h-96 overflow-y-auto">
                    <Table>
                      <TableHeader>
                        {batchResultsTable.getHeaderGroups().map((headerGroup) => (
                          <TableRow key={headerGroup.id}>
                            {headerGroup.headers.map((header) => (
                              <TableHead key={header.id}>
                                {header.isPlaceholder
                                  ? null
                                  : flexRender(
                                      header.column.columnDef.header,
                                      header.getContext()
                                    )}
                              </TableHead>
                            ))}
                          </TableRow>
                        ))}
                      </TableHeader>
                      <TableBody>
                        {batchResultsTable.getRowModel().rows?.length ? (
                          batchResultsTable.getRowModel().rows.map((row) => (
                            <TableRow
                              key={row.id}
                              data-state={row.getIsSelected() && "selected"}
                              className={row.original.error ? "bg-destructive/10" : ""}
                            >
                              {row.getVisibleCells().map((cell) => (
                                <TableCell key={cell.id}>
                                  {flexRender(
                                    cell.column.columnDef.cell,
                                    cell.getContext()
                                  )}
                                </TableCell>
                              ))}
                            </TableRow>
                          ))
                        ) : (
                          <TableRow>
                            <TableCell
                              colSpan={batchResultsColumns.length}
                              className="h-24 text-center"
                            >
                              No results
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </div>
                </div>
                <div className="pt-2 text-sm text-muted-foreground">
                  Total: {batchResults.length} locations processed
                  {batchResults.reduce((sum, r) => sum + r.agencies.length, 0) > 0 && (
                    <span className="ml-2">
                      • {batchResults.reduce((sum, r) => sum + r.agencies.length, 0)} agencies found
                    </span>
                  )}
                </div>
              </div>
            )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="lists" className="mt-6">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>My Lists</CardTitle>
                    <CardDescription>Manage your saved lists</CardDescription>
                  </div>
                  <Dialog open={createListOpen} onOpenChange={setCreateListOpen}>
                    <DialogTrigger asChild>
                      <Button variant="outline">
                        <Plus className="mr-2 h-4 w-4" />
                        New List
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Create New List</DialogTitle>
                        <DialogDescription>
                          Create a new list to save selected agencies
                        </DialogDescription>
                      </DialogHeader>
                      <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                          <Label htmlFor="list-name-tab">List Name</Label>
                          <Input
                            id="list-name-tab"
                            value={newListName}
                            onChange={(e) => setNewListName(e.target.value)}
                            placeholder="My Agency List"
                          />
                        </div>
                        <div className="grid gap-2">
                          <Label htmlFor="list-description-tab">Description (optional)</Label>
                          <Input
                            id="list-description-tab"
                            value={newListDescription}
                            onChange={(e) => setNewListDescription(e.target.value)}
                            placeholder="Description of this list"
                          />
                        </div>
                      </div>
                      <DialogFooter>
                        <Button onClick={handleCreateList}>Create List</Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent>
                {lists.length === 0 ? (
                  <div className="py-8 text-center text-muted-foreground">
                    No lists created yet. Create a list to organize your agencies.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {lists.map((list) => (
                  <div
                    key={list.id}
                    className="flex items-center justify-between rounded-lg border p-4"
                  >
      <div>
                      <h3 className="font-semibold">{list.name}</h3>
                      {list.description && (
                        <p className="text-sm text-muted-foreground">
                          {list.description}
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground">
                        Created: {new Date(list.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSelectedListId(list.id)
                          handleDownload("csv")
                        }}
                      >
                        <Download className="mr-2 h-4 w-4" />
                        CSV
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setSelectedListId(list.id)
                          handleDownload("json")
                        }}
                      >
                        <Download className="mr-2 h-4 w-4" />
                        JSON
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={async () => {
                          if (confirm(`Delete "${list.name}"?`)) {
                            await deleteList(list.id)
                            await loadLists()
                            if (selectedListId === list.id) setSelectedListId("")
                          }
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Add/Edit County Dialog */}
        <Dialog open={countyDialogOpen} onOpenChange={setCountyDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {editingCounty ? "Edit County" : "Add County"}
              </DialogTitle>
              <DialogDescription>
                {editingCounty
                  ? "Update the state and location for this county."
                  : "Add a new state/county pair to the batch scraper."}
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="county-state">State (2-letter code)</Label>
                <Input
                  id="county-state"
                  value={newCountyState}
                  onChange={(e) => setNewCountyState(e.target.value.toUpperCase())}
                  placeholder="e.g., NC"
                  maxLength={2}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="county-location">Location</Label>
                <Input
                  id="county-location"
                  value={newCountyLocation}
                  onChange={(e) => setNewCountyLocation(e.target.value)}
                  placeholder="e.g., Raleigh"
                />
              </div>
      </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setCountyDialogOpen(false)
                  setEditingCounty(null)
                  setNewCountyState("")
                  setNewCountyLocation("")
                }}
              >
                Cancel
              </Button>
              <Button onClick={editingCounty ? handleUpdateCounty : handleAddCounty}>
                {editingCounty ? "Update" : "Add"} County
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  )
}

export default App
