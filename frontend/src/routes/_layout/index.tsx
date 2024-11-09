import {
  Box,
  Container,
  Text,
  FormControl,
  FormErrorMessage,
  FormLabel,
  Input,
  Button,
} from "@chakra-ui/react";
import { createFileRoute } from "@tanstack/react-router";
import useAuth from "../../hooks/useAuth";
import { type SubmitHandler, useForm } from "react-hook-form"
import { InfringementCheckService, ApiError } from "../../client"
import useCustomToast from "../../hooks/useCustomToast"
import { useMutation } from "@tanstack/react-query"
import { handleError } from "../../utils"
import { useState } from "react"


export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
});

interface InfringementCheckForm {
  company_name: string;
  patent_id: string;
}

function Dashboard() {
  const { user: currentUser } = useAuth();
  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<InfringementCheckForm>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      company_name: "",
      patent_id: "",
    },
  });
  const showToast = useCustomToast()
  const [report, setReport] = useState("")
  const mutation = useMutation({
    mutationFn: async (data: InfringementCheckForm) =>
      InfringementCheckService.createInfringementCheck({ requestBody: data }),
    onSuccess: (data) => {
      setReport(JSON.stringify(data, null, 2));
      showToast("Success!", "Create Infringement Check successfully.", "success")
    },
    onError: (err: ApiError) => {
      handleError(err, showToast)
    },
  })

  const onSubmit: SubmitHandler<InfringementCheckForm> = (data) => {
    mutation.mutate(data)
  }

  return (
    <>
      <Container maxW="full">
        <Box pt={12} m={4}>
          <Text fontSize="2xl">
            Hi, {currentUser?.full_name || currentUser?.email} 👋🏼
          </Text>
        </Box>
        <Box pt={12} m={4}>
          <Text fontSize="2xl">Infringement Check</Text>
        </Box>
        <Box pt={12} m={4} as="form"
          onSubmit={handleSubmit(onSubmit)}>
          <FormControl isRequired isInvalid={!!errors.company_name}>
            <FormLabel htmlFor="company_name">Company Name</FormLabel>
            <Input
              id="company_name"
              {...register("company_name", {
                required: "Company name is required",
              })}
              placeholder="company name"
              type="text"
            />
            {errors.company_name && (
              <FormErrorMessage>{errors.company_name.message}</FormErrorMessage>
            )}
          </FormControl>
          <FormControl mt={4} isInvalid={!!errors.patent_id}>
            <FormLabel htmlFor="patent_id">Patent ID</FormLabel>
            <Input
              id="patent_id"
              {...register("patent_id")}
              placeholder="patent id"
              type="text"
            />
            {errors.patent_id && (
              <FormErrorMessage>{errors.patent_id.message}</FormErrorMessage>
            )}
            <Button
              variant="primary"
              mt={4}
              type="submit"
              isLoading={isSubmitting}
            >
              Submit
            </Button>
          </FormControl>
        </Box>
        <Box pt={12} m={4}>
          <Text fontSize="2xl">
            Infringement Check Result:
          </Text>
          {report}
        </Box>
      </Container>
    </>
  );
}
